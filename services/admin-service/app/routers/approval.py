"""
Approval router — handles incident approval/rejection.

Provides:
- POST /approval/approve/{incident_id}  — fallback approval (no Vapi needed)
- POST /approval/reject/{incident_id}   — fallback rejection
- POST /approval/notify/{incident_id}   — trigger Vapi voice call
- POST /approval/vapi-webhook           — webhook callback from Vapi
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.tables import AuditLog, Incident
from app.services.docker_controller import DockerController
from app.services.vapi_service import trigger_voice_call

logger = logging.getLogger("approval")

router = APIRouter(prefix="/approval", tags=["approval"])

_controller = DockerController()


class ApprovalResponse(BaseModel):
    incident_id: int
    status: str
    action_taken: Optional[str] = None
    action_result: Optional[str] = None
    message: str


def _get_incident(db: Session, incident_id: int) -> Incident:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


def _log_audit(db: Session, incident_id: int, action: str, approved_by: str, details: str) -> None:
    audit = AuditLog(
        incident_id=incident_id,
        action=action,
        approved_by=approved_by,
        details=details,
    )
    db.add(audit)
    db.commit()


def _extract_action_type(incident: Incident) -> str:
    """Extract action_type from suggested_solution or fall back to error_summary issue code."""
    sol = (incident.suggested_solution or "").lower()
    if "[action: restart]" in sol:
        return "restart"
    if "[action: scale]" in sol:
        return "scale"

    # Fallback: derive action from the issue code in error_summary
    summary = (incident.error_summary or "").upper()
    if "SVC_DOWN_001" in summary:
        return "restart"
    if "SVC_LATENCY_002" in summary:
        return "scale"
    if "APP_NPE_003" in summary:
        return "none"

    return "none"


def _execute_remediation(incident: Incident, db: Session) -> tuple[str, str]:
    """Execute the remediation action based on the incident's suggested solution."""
    action_type = _extract_action_type(incident)

    if action_type == "restart":
        result = _controller.restart_service(incident.service_name)
        return "restart", f"success={result.success} | {result.message}"

    if action_type == "scale":
        result = _controller.scale_service(incident.service_name, 2)
        return "scale", f"success={result.success} | {result.message}"

    return "none", "No infrastructure action required — manual intervention suggested"
@router.post("/approve/{incident_id}", response_model=ApprovalResponse)
def approve_incident(
    incident_id: int,
    approved_by: str = "fallback_api",
    db: Session = Depends(get_db),
) -> dict:
    """
    Approve an incident and execute the suggested remediation action.
    This is the fallback endpoint — use when Vapi is unavailable.
    """
    incident = _get_incident(db, incident_id)

    if incident.status in ("RESOLVED", "REJECTED"):
        raise HTTPException(status_code=400, detail=f"Incident already {incident.status}")

    # Transition: → APPROVED
    incident.status = "APPROVED"
    incident.updated_at = datetime.utcnow()
    db.commit()

    _log_audit(db, incident_id, "approved", approved_by, f"Incident approved via fallback API")

    # Execute remediation → ACTION_TAKEN
    action_type, action_result = _execute_remediation(incident, db)

    incident.status = "ACTION_TAKEN"
    incident.updated_at = datetime.utcnow()
    db.commit()

    _log_audit(db, incident_id, f"action:{action_type}", "system", action_result)

    # If action succeeded, mark RESOLVED
    if "success=True" in action_result or action_type == "none":
        incident.status = "RESOLVED"
        incident.updated_at = datetime.utcnow()
        db.commit()
        _log_audit(db, incident_id, "resolved", "system", "Incident resolved after remediation")

    return {
        "incident_id": incident_id,
        "status": incident.status,
        "action_taken": action_type,
        "action_result": action_result,
        "message": f"Incident #{incident_id} approved and remediation executed",
    }


@router.post("/reject/{incident_id}", response_model=ApprovalResponse)
def reject_incident(
    incident_id: int,
    rejected_by: str = "fallback_api",
    reason: str = "Rejected by operator",
    db: Session = Depends(get_db),
) -> dict:
    """Reject an incident — no remediation will be performed."""
    incident = _get_incident(db, incident_id)

    if incident.status in ("RESOLVED", "REJECTED"):
        raise HTTPException(status_code=400, detail=f"Incident already {incident.status}")

    incident.status = "REJECTED"
    incident.updated_at = datetime.utcnow()
    db.commit()

    _log_audit(db, incident_id, "rejected", rejected_by, reason)

    return {
        "incident_id": incident_id,
        "status": "REJECTED",
        "action_taken": None,
        "action_result": None,
        "message": f"Incident #{incident_id} rejected: {reason}",
    }


@router.post("/resolve/{incident_id}", response_model=ApprovalResponse)
def resolve_incident(
    incident_id: int,
    resolved_by: str = "operator",
    db: Session = Depends(get_db),
) -> dict:
    """Manually resolve an incident (e.g. after a call transfer)."""
    incident = _get_incident(db, incident_id)

    if incident.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Incident already RESOLVED")

    incident.status = "RESOLVED"
    incident.updated_at = datetime.utcnow()
    db.commit()

    _log_audit(db, incident_id, "resolved", resolved_by, "Incident resolved manually by operator")

    return {
        "incident_id": incident_id,
        "status": "RESOLVED",
        "action_taken": None,
        "action_result": "Manual Resolution",
        "message": f"Incident #{incident_id} resolved manually",
    }


@router.post("/notify/{incident_id}")
async def notify_via_vapi(
    incident_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Trigger a Vapi voice call to notify the on-call engineer."""
    incident = _get_incident(db, incident_id)

    # Transition: → USER_NOTIFIED
    incident.status = "USER_NOTIFIED"
    incident.updated_at = datetime.utcnow()
    db.commit()

    _log_audit(db, incident_id, "notify", "system", "Voice notification triggered")

    result = await trigger_voice_call(
        incident_id=incident.id,
        service_name=incident.service_name,
        error_summary=incident.error_summary or "",
        suggested_solution=incident.suggested_solution or "",
    )

    return {
        "incident_id": incident_id,
        "notification": result,
    }


@router.post("/vapi-webhook")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Webhook endpoint called by Vapi during/after the voice call.
    Handles call events like function calls (approve/reject).
    """
    body = await request.json()
    logger.info(f"Vapi webhook received: {body}")

    message_type = body.get("message", {}).get("type", "")

    if message_type == "function-call":
        function_name = body.get("message", {}).get("functionCall", {}).get("name", "")
        parameters = body.get("message", {}).get("functionCall", {}).get("parameters", {})
        incident_id = parameters.get("incident_id")

        if incident_id and function_name == "approve":
            # Re-use approve logic
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident and incident.status not in ("RESOLVED", "REJECTED"):
                incident.status = "APPROVED"
                incident.updated_at = datetime.utcnow()
                db.commit()
                _log_audit(db, incident_id, "approved", "vapi_voice_call", "Approved via voice call")

                action_type, action_result = _execute_remediation(incident, db)
                incident.status = "ACTION_TAKEN"
                db.commit()
                _log_audit(db, incident_id, f"action:{action_type}", "system", action_result)

                if "success=True" in action_result or action_type == "none":
                    incident.status = "RESOLVED"
                    db.commit()

                return {"result": f"Incident #{incident_id} approved and remediation executed"}

        elif incident_id and function_name == "reject":
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident and incident.status not in ("RESOLVED", "REJECTED"):
                incident.status = "REJECTED"
                db.commit()
                _log_audit(db, incident_id, "rejected", "vapi_voice_call", "Rejected via voice call")
                return {"result": f"Incident #{incident_id} rejected via voice call"}

    return {"status": "received"}