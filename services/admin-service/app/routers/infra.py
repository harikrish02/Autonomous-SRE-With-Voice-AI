from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.tables import AuditLog, ServiceState
from app.services.docker_controller import DockerController

router = APIRouter(prefix="/infra", tags=["infra"])

# Singleton controller instance
_controller = DockerController()


class ActionResponse(BaseModel):
    success: bool
    service_name: str
    action: str
    message: str
    details: Optional[str] = None


class ServiceStatusResponse(BaseModel):
    service_name: str
    status: str
    replicas: int
    details: Optional[str] = None


def _log_audit(db: Session, action: str, service_name: str, success: bool, details: str, incident_id: Optional[int] = None) -> None:
    audit = AuditLog(
        incident_id=incident_id,
        action=f"{action}:{service_name}",
        approved_by="system",
        details=f"success={success} | {details}",
    )
    db.add(audit)
    db.commit()


def _update_service_state(db: Session, service_name: str, status: str, replicas: int) -> None:
    state = db.query(ServiceState).filter(ServiceState.service_name == service_name).first()
    if state:
        state.status = status
        state.replicas = replicas
        state.last_checked = datetime.utcnow()
        state.updated_at = datetime.utcnow()
    else:
        state = ServiceState(
            service_name=service_name,
            status=status,
            replicas=replicas,
        )
        db.add(state)
    db.commit()


@router.post("/restart/{service_name}", response_model=ActionResponse)
def restart_service(
    service_name: str,
    incident_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    result = _controller.restart_service(service_name)

    _log_audit(db, "restart", service_name, result.success, result.message, incident_id)

    if result.success:
        _update_service_state(db, service_name, "running", 1)

    return {
        "success": result.success,
        "service_name": result.service_name,
        "action": result.action,
        "message": result.message,
        "details": result.details,
    }


@router.post("/scale/{service_name}", response_model=ActionResponse)
def scale_service(
    service_name: str,
    replicas: int = Query(2, ge=1, le=10),
    incident_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    result = _controller.scale_service(service_name, replicas)

    _log_audit(db, "scale", service_name, result.success, f"replicas={replicas} | {result.message}", incident_id)

    if result.success:
        _update_service_state(db, service_name, "running", replicas)

    return {
        "success": result.success,
        "service_name": result.service_name,
        "action": result.action,
        "message": result.message,
        "details": result.details,
    }

@router.get("/status/{service_name}", response_model=ServiceStatusResponse)
def get_service_status(service_name: str, db: Session = Depends(get_db)) -> dict:
    status = _controller.get_status(service_name)

    _update_service_state(db, service_name, status.status, status.replicas)

    return {
        "service_name": status.service_name,
        "status": status.status,
        "replicas": status.replicas,
        "details": status.details,
    }


@router.get("/status", response_model=list[ServiceStatusResponse])
def get_all_statuses(db: Session = Depends(get_db)) -> list[dict]:
    statuses = _controller.get_all_statuses()

    for s in statuses:
        _update_service_state(db, s.service_name, s.status, s.replicas)

    return [
        {
            "service_name": s.service_name,
            "status": s.status,
            "replicas": s.replicas,
            "details": s.details,
        }
        for s in statuses
    ]


@router.post("/stop/{service_name}", response_model=ActionResponse)
def stop_service(
    service_name: str,
    db: Session = Depends(get_db),
) -> dict:
    """Stop a Docker container to simulate a service being down."""
    result = _controller.stop_service(service_name)
    _log_audit(db, "stop", service_name, result.success, result.message)
    if result.success:
        _update_service_state(db, service_name, "exited", 0)
    return {
        "success": result.success,
        "service_name": result.service_name,
        "action": result.action,
        "message": result.message,
        "details": result.details,
    }


@router.post("/simulate/high-latency/{service_name}")
def simulate_high_latency(service_name: str, db: Session = Depends(get_db)) -> dict:
    """Inject a single high-latency log entry for a service."""
    import os, uuid
    from app.models.tables import Log
    threshold = float(os.getenv("LATENCY_THRESHOLD_MS", "3000"))
    trace_id = str(uuid.uuid4())
    duration = round(threshold + 500, 2)
    log = Log(
        trace_id=trace_id,
        service_name=service_name,
        status="LATENCY",
        message=f"{trace_id}|APICall|LATENCY|timetaken={duration}ms|{service_name}",
        duration_ms=duration,
    )
    db.add(log)
    db.commit()
    return {"success": True, "message": f"Injected 1 high-latency log for {service_name} ({duration}ms > {threshold}ms threshold)"}


@router.post("/simulate/python-error/{service_name}")
def simulate_python_error(service_name: str, db: Session = Depends(get_db)) -> dict:
    """Inject a single simulated application error log entry for a service."""
    import uuid
    from app.models.tables import Log
    trace_id = str(uuid.uuid4())
    
    error_type = "NullPointerException"
    message = f"NullPointerException: {service_name} — object reference is null at processRequest() line 42"
    
    if service_name == "service-a":
        error_type = "BusinessServiceException"
        message = f"Business service exception: {service_name} rule violation detected in validation logic"
    elif service_name == "service-c":
        error_type = "AuthenticationError"
        message = f"error authenticating the user 401: {service_name} token expired or invalid"

    log = Log(
        trace_id=trace_id,
        service_name=service_name,
        status="ERROR",
        error_type=error_type,
        message=message,
        duration_ms=0,
    )
    db.add(log)
    db.commit()
    return {"success": True, "message": f"Injected 1 {error_type} error for {service_name}"}