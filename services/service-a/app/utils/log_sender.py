import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("log_sender")

ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://localhost:8000")


async def send_log(
    trace_id: str,
    service_name: str,
    status: str,
    error_type: Optional[str] = None,
    message: Optional[str] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """Send a structured log entry to the admin service. Fire-and-forget."""
    payload = {
        "trace_id": trace_id,
        "service_name": service_name,
        "status": status,
        "error_type": error_type,
        "message": message,
        "duration_ms": duration_ms,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{ADMIN_SERVICE_URL}/logs/", json=payload)
            if resp.status_code != 201:
                logger.warning(f"Log ingestion returned {resp.status_code}: {resp.text[:100]}")
    except Exception as exc:
        logger.debug(f"Failed to send log to {ADMIN_SERVICE_URL}: {exc}")