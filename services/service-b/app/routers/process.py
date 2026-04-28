import os
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Query

from app.utils.failure_simulator import simulate_failure
from app.utils.log_sender import send_log

router = APIRouter()

SERVICE_NAME = "service-b"
SERVICE_C_URL = os.getenv("SERVICE_C_URL", "http://localhost:8003")


@router.get("/process")
async def process(
    fail: Optional[str] = Query(None, description="Failure mode: timeout, error, high_latency"),
    fail_at: Optional[str] = Query(None, description="Target service to fail: service-b, service-c"),
    x_trace_id: Optional[str] = Header(None),
) -> dict:
    trace_id = x_trace_id or str(uuid.uuid4())
    start_time = time.time()

    try:
        if fail and (fail_at is None or fail_at == SERVICE_NAME):
            await simulate_failure(fail, SERVICE_NAME)

        async with httpx.AsyncClient(timeout=35.0) as client:
            params = {}
            if fail and fail_at and fail_at != SERVICE_NAME:
                params["fail"] = fail
                params["fail_at"] = fail_at
            response = await client.get(
                f"{SERVICE_C_URL}/process",
                params=params,
                headers={"X-Trace-Id": trace_id},
            )

        if response.status_code != 200:
            error_detail = response.json().get("detail", "Unknown downstream error")
            duration_ms = round((time.time() - start_time) * 1000, 2)
            err_type = "NullPointerException" if "NullPointerException" in error_detail else "downstream_error"
            await send_log(trace_id, SERVICE_NAME, "ERROR", error_type=err_type, message=error_detail, duration_ms=duration_ms)
            raise HTTPException(status_code=502, detail=f"{SERVICE_NAME} received error from service-c: {error_detail}")

        downstream_result = response.json()
        duration_ms = round((time.time() - start_time) * 1000, 2)

        status_label = "LATENCY" if duration_ms > 3000 else "SUCCESS"
        message = f"{trace_id}|APICall|{status_label}|timetaken={duration_ms}ms|service-b"
        await send_log(trace_id, SERVICE_NAME, status_label, message=message, duration_ms=duration_ms)

        return {
            "service": SERVICE_NAME,
            "traceId": trace_id,
            "status": "success",
            "message": f"{SERVICE_NAME} processed successfully",
            "duration_ms": duration_ms,
            "downstream": downstream_result,
        }

    except HTTPException:
        raise
    except httpx.TimeoutException:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        await send_log(trace_id, SERVICE_NAME, "ERROR", error_type="timeout", message="downstream service-c timed out", duration_ms=duration_ms)
        raise HTTPException(status_code=504, detail=f"{SERVICE_NAME}: downstream service-c timed out")
    except httpx.ConnectError:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        await send_log(trace_id, SERVICE_NAME, "ERROR", error_type="connection_error", message="service-c is unavailable", duration_ms=duration_ms)
        raise HTTPException(status_code=503, detail=f"{SERVICE_NAME}: service-c is unavailable")
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        await send_log(trace_id, SERVICE_NAME, "ERROR", error_type="internal_error", message=str(exc), duration_ms=duration_ms)
        raise HTTPException(status_code=500, detail=str(exc))