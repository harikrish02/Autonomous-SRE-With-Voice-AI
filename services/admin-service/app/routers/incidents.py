from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import IncidentResponse, IncidentUpdateStatus
from app.models.tables import Incident

router = APIRouter(prefix="/incidents", tags=["incidents"])

VALID_STATUSES = ["DETECTED", "ANALYZED", "USER_NOTIFIED", "APPROVED", "ACTION_TAKEN", "RESOLVED", "REJECTED"]


@router.get("/", response_model=list[IncidentResponse])
def list_incidents(
    service: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Incident]:
    query = db.query(Incident)
    if service:
        query = query.filter(Incident.service_name == service)
    if status:
        query = query.filter(Incident.status == status)
    return query.order_by(desc(Incident.created_at)).limit(limit).all()


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: int,
    body: IncidentUpdateStatus,
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {VALID_STATUSES}")
    incident.status = body.status
    incident.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(incident)
    return incident