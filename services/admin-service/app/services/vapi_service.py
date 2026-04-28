"""
Vapi integration service — triggers voice calls for incident approval.

When Vapi is configured (VAPI_API_KEY set), this sends a real voice call.
When Vapi is not configured, it logs the intent and skips the call.
The fallback approval API can always be used regardless.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("vapi_service")

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_PHONE_NUMBER = os.getenv("VAPI_PHONE_NUMBER", "")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://localhost:8000")
NGROK_URL = os.getenv("NGROK_URL", "")


def is_vapi_configured() -> bool:
    """Check if Vapi credentials are available."""
    return bool(VAPI_API_KEY and VAPI_PHONE_NUMBER)


async def trigger_voice_call(
    incident_id: int,
    service_name: str,
    error_summary: str,
    suggested_solution: str,
) -> dict:
    """
    Trigger a Vapi voice call to notify the on-call engineer about an incident.

    The voice assistant will:
    1. Inform the user about the incident
    2. Describe the suggested solution
    3. Ask for approval to proceed

    Returns a dict with call status info.
    """
    if not is_vapi_configured():
        logger.warning(
            f"Vapi not configured — skipping voice call for incident #{incident_id}. "
            f"Use fallback API: POST /approval/approve/{incident_id}"
        )
        return {
            "status": "skipped",
            "reason": "Vapi not configured (VAPI_API_KEY or VAPI_PHONE_NUMBER missing)",
            "incident_id": incident_id,
            "fallback_url": f"{ADMIN_SERVICE_URL}/approval/approve/{incident_id}",
        }

    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": VAPI_PHONE_NUMBER,
        },
        "assistantOverrides": {
            "variableValues": {
                "service_name": service_name,
                "resolution_steps": suggested_solution,
                "current_problem": error_summary
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.vapi.ai/call/phone",
                json=payload,
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code in (200, 201):
            call_data = response.json()
            logger.info(f"Vapi call initiated for incident #{incident_id}: {call_data.get('id', 'unknown')}")
            return {
                "status": "call_initiated",
                "incident_id": incident_id,
                "call_id": call_data.get("id"),
                "phone_number": VAPI_PHONE_NUMBER,
            }
        else:
            logger.error(f"Vapi call failed: {response.status_code} — {response.text}")
            return {
                "status": "call_failed",
                "incident_id": incident_id,
                "error": f"Vapi returned {response.status_code}: {response.text[:200]}",
                "fallback_url": f"{ADMIN_SERVICE_URL}/approval/approve/{incident_id}",
            }

    except Exception as exc:
        logger.error(f"Vapi call error for incident #{incident_id}: {exc}")
        return {
            "status": "call_error",
            "incident_id": incident_id,
            "error": str(exc),
            "fallback_url": f"{ADMIN_SERVICE_URL}/approval/approve/{incident_id}",
        }