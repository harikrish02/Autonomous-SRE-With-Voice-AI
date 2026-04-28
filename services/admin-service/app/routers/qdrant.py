from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.qdrant_service import get_best_solution, query_runbook

router = APIRouter(prefix="/qdrant", tags=["qdrant"])


class RunbookQueryRequest(BaseModel):
    description: str
    top_k: int = 3


class RunbookMatch(BaseModel):
    score: float
    error_pattern: str
    root_cause: str
    recommended_fix: str
    action_type: str
    applicable_services: str
    severity: str


class RunbookQueryResponse(BaseModel):
    query: str
    matches: list[RunbookMatch]


@router.post("/query", response_model=RunbookQueryResponse)
def query_qdrant(body: RunbookQueryRequest) -> dict:
    matches = query_runbook(body.description, top_k=body.top_k)
    return {"query": body.description, "matches": matches}


@router.get("/search", response_model=RunbookQueryResponse)
def search_qdrant(
    q: str = Query(..., description="Error description to search"),
    top_k: int = Query(3, ge=1, le=10),
) -> dict:
    matches = query_runbook(q, top_k=top_k)
    return {"query": q, "matches": matches}
