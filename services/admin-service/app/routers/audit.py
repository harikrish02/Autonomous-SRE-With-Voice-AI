from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.tables import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: int
    incident_id: Optional[int] = None
    action: str
    approved_by: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    incident_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    query = db.query(AuditLog)
    if incident_id is not None:
        query = query.filter(AuditLog.incident_id == incident_id)
    return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()