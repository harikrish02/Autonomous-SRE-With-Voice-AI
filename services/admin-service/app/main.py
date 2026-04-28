import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db
from app.routers.approval import router as approval_router
from app.routers.audit import router as audit_router
from app.routers.incidents import router as incidents_router
from app.routers.infra import router as infra_router
from app.routers.logs import router as logs_router
from app.routers.qdrant import router as qdrant_router
from app.routers.mcp import router as mcp_router
from app.services.watchdog import watchdog_loop

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Admin Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router)
app.include_router(incidents_router)
app.include_router(qdrant_router)
app.include_router(infra_router)
app.include_router(approval_router)
app.include_router(audit_router)
app.include_router(mcp_router)


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    asyncio.create_task(watchdog_loop())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "admin-service"}