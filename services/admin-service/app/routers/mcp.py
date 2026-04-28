import logging
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

logger = logging.getLogger("mcp")

from app.models.database import get_db
from app.models.tables import Incident, AuditLog
from app.routers.infra import restart_service, scale_service, stop_service

router = APIRouter(prefix="/mcp", tags=["mcp"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

class MCPRequest(BaseModel):
    prompt: str

class MCPResponse(BaseModel):
    success: bool
    action: str
    service_name: str
    message: str

async def call_gemini(prompt: str) -> dict:
    """Use Gemini REST API to extract intent from natural language prompt."""
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is not configured in .env")

    import asyncio, json

    models = ["gemini-2.5-flash", "gemini-flash-latest"]
    system_prompt = (
        "You are an AI DevOps router. Given the prompt, determine the action "
        "(restart, scale, stop, call_transfer), the target service (service-a, service-b, service-c), "
        "optionally replicas (int, default 3 for scale), and whether the user approves "
        "or rejects the action (approval_status: 'approved' or 'rejected'). "
        "Return strictly valid JSON with keys: action, service_name, replicas, approval_status.\n"
        f"Prompt: {prompt}"
    )
    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    headers = {"X-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}

    last_error = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(2):
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            if response.status_code in (429, 503):
                last_error = f"{model} returned {response.status_code} (attempt {attempt+1})"
                await asyncio.sleep(1)  # fast 1s backoff for voice call responsiveness
                continue
            last_error = f"Gemini API error ({response.status_code}): {response.text[:200]}"
            break  # non-retryable error, try next model

    raise Exception(f"All Gemini models failed. Last error: {last_error}")


async def call_ollama(prompt: str) -> dict:
    """Use local Ollama API as a fallback when Gemini is rate-limited."""
    import json
    url = "http://ollama:11434/api/generate"
    
    system_prompt = (
        "You are an AI DevOps router. Given the prompt, determine the action "
        "(restart, scale, stop, call_transfer), the target service (service-a, service-b, service-c), "
        "optionally replicas (int, default 2 for scale), and whether the user approves "
        "or rejects the action (approval_status: 'approved' or 'rejected'). "
        "Return ONLY strictly valid JSON with keys: action, service_name, replicas, approval_status."
    )
    
    payload = {
        "model": "llama3",
        "prompt": f"{system_prompt}\n\nUser Prompt: {prompt}",
        "stream": False,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return json.loads(data["response"])
            else:
                raise Exception(f"Ollama error ({response.status_code}): {response.text[:100]}")
    except Exception as e:
        raise Exception(f"Ollama fallback failed: {str(e)}")

@router.post("/execute", response_model=MCPResponse)
async def execute_mcp_command(request: MCPRequest, db: Session = Depends(get_db)):
    """
    Exposes an MCP-like interface where a Gemini agent decides which 
    backend infra controller to invoke based on natural language.
    All actions invoked here are automatically captured in AuditLog 
    via the underlying infra routers.
    """
    logger.info(f"[MCP] Incoming request — prompt: {request.prompt}")
    ai_source = "gemini"
    try:
        if not GEMINI_API_KEY:
            ai_source = "keyword_fallback"
            # Fallback simple keyword matching if key is missing (for local testing without keys)
            action = "unknown"
            if "restart" in request.prompt.lower(): action = "restart"
            elif "scale" in request.prompt.lower(): action = "scale"
            elif "stop" in request.prompt.lower(): action = "stop"
            
            service_name = "service-a"
            if "service-b" in request.prompt.lower(): service_name = "service-b"
            if "service-c" in request.prompt.lower(): service_name = "service-c"
            
            approval_status = "rejected" if "reject" in request.prompt.lower() or "deny" in request.prompt.lower() else "approved"
            intent = {"action": action, "service_name": service_name, "replicas": 2, "approval_status": approval_status}
        else:
            try:
                intent = await call_gemini(request.prompt)
            except Exception as e:
                logger.warning(f"Gemini failed with {e}, falling back to instant keyword parser.")
                ai_source = "keyword_fallback"
                
                action = "unknown"
                if "restart" in request.prompt.lower(): action = "restart"
                elif "scale" in request.prompt.lower(): action = "scale"
                elif "stop" in request.prompt.lower(): action = "stop"
                
                service_name = "service-a"
                if "service-b" in request.prompt.lower(): service_name = "service-b"
                if "service-c" in request.prompt.lower(): service_name = "service-c"
                
                approval_status = "rejected" if "reject" in request.prompt.lower() or "deny" in request.prompt.lower() else "approved"
                intent = {"action": action, "service_name": service_name, "replicas": 3, "approval_status": approval_status}

        action = str(intent.get("action") or "unknown").lower()
        service_name = str(intent.get("service_name") or "unknown").lower()
        replicas = intent.get("replicas") or 3
        approval_status = str(intent.get("approval_status") or "approved").lower()

        from app.models.tables import AuditLog
        prompt_text = request.prompt

        if approval_status == "rejected":
            db.add(AuditLog(
                action=f"{action}:{service_name}",
                approved_by="mcp_agent",
                details=f"status=rejected | source={ai_source} | prompt={prompt_text} | Action was rejected by user, operation aborted."
            ))
            db.commit()
            return {"success": True, "action": action, "service_name": service_name, "message": "Action was rejected by user. Logged to audit."}

        # Approved — execute and log with prompt
        if action == "restart":
            result = restart_service(service_name=service_name, incident_id=None, db=db)
        elif action == "scale":
            result = scale_service(service_name=service_name, replicas=replicas, incident_id=None, db=db)
        elif action == "stop":
            result = stop_service(service_name=service_name, db=db)
        elif action == "call_transfer":
            # Find the active incident for this service and mark it as TRANSFERRED
            active_statuses = ["DETECTED", "ANALYZED", "USER_NOTIFIED", "APPROVED", "ACTION_TAKEN"]
            incident = (
                db.query(Incident)
                .filter(Incident.service_name == service_name, Incident.status.in_(active_statuses))
                .order_by(Incident.created_at.desc())
                .first()
            )
            
            if incident:
                incident.status = "TRANSFERRED"
                incident.updated_at = datetime.utcnow()
                db.commit()
                
                result = {"success": True, "message": f"Incident #{incident.id} transferred to manual support."}
            else:
                result = {"success": True, "message": "No active incident found to transfer, but call transfer logged."}
            
            # Log the transfer in audit
            db.add(AuditLog(
                action=f"transfer:{service_name}",
                approved_by="mcp_agent",
                details=f"status=transferred | source={ai_source} | prompt={prompt_text} | {result['message']}"
            ))
            db.commit()
            return {"success": True, "action": action, "service_name": service_name, "message": result["message"]}
        else:
            db.add(AuditLog(
                action=f"unknown:{service_name}",
                approved_by="mcp_agent",
                details=f"status=unknown_action | source={ai_source} | prompt={prompt_text} | action={action}"
            ))
            db.commit()
            return {"success": False, "action": action, "service_name": service_name, "message": f"Unknown action: {action}"}

        # Overwrite the auto-created audit entry with the prompt context
        db.add(AuditLog(
            action=f"mcp:{action}:{service_name}",
            approved_by="mcp_agent",
            details=f"status=approved | source={ai_source} | prompt={prompt_text} | result={result['message']}"
        ))
        db.commit()
        return {"success": result["success"], "action": action, "service_name": service_name, "message": result["message"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
