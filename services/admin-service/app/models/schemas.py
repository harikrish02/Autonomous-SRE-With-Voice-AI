from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LogCreate(BaseModel):
    trace_id: str
    service_name: str
    status: str  # SUCCESS, ERROR, LATENCY
    error_type: Optional[str] = None
    message: Optional[str] = None
    duration_ms: Optional[float] = None


class LogResponse(BaseModel):
    id: int
    trace_id: str
    service_name: str
    timestamp: datetime
    status: str
    error_type: Optional[str] = None
    message: Optional[str] = None
    duration_ms: Optional[float] = None

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    id: int
    trace_id: Optional[str] = None
    service_name: str
    severity: str
    status: str
    error_summary: Optional[str] = None
    suggested_solution: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IncidentUpdateStatus(BaseModel):
    status: str