import time
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from app.utils.failure_simulator import simulate_failure
from app.utils.log_sender import send_log

router = APIRouter()

SERVICE_NAME = "service-c"


@router.get("/process")
async def process(
    fail: Optional[str] = Query(None, description="Failure mode: timeout, error, high_latency"),
    fail_at: Optional[str] = Query(None, description="Target service to fail"),
    x_trace_id: Optional[str] = Header(None),
) -> dict:
    trace_id = x_trace_id or str(uuid.uuid4())
    start_time = time.time()

    try:
        if fail and (fail_at is None or fail_at == SERVICE_NAME):
            await simulate_failure(fail, SERVICE_NAME)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        status_label = "LATENCY" if duration_ms > 3000 else "SUCCESS"
        message = f"{trace_id}|APICall|{status_label}|timetaken={duration_ms}ms|service-c"
        await send_log(trace_id, SERVICE_NAME, status_label, message=message, duration_ms=duration_ms)

        return {
            "service": SERVICE_NAME,
            "traceId": trace_id,
            "status": "success",
            "message": f"{SERVICE_NAME} processed successfully",
            "duration_ms": duration_ms,
        }
    except HTTPException as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        if "NullPointerException" in (exc.detail or ""):
            error_type = "NullPointerException"
        elif exc.status_code == 504:
            error_type = "timeout"
        else:
            error_type = "internal_error"
        await send_log(trace_id, SERVICE_NAME, "ERROR", error_type=error_type, message=exc.detail, duration_ms=duration_ms)
        raise
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        await send_log(trace_id, SERVICE_NAME, "ERROR", error_type="internal_error", message=str(exc), duration_ms=duration_ms)
        raise HTTPException(status_code=500, detail=str(exc))