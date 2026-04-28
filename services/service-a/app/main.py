import asyncio
import random
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.process import router as process_router
from app.utils.log_sender import send_log

app = FastAPI(title="Service A", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "service-a"}


async def _background_log_emitter():
    """Emit a normal operational log every 10 seconds."""
    await asyncio.sleep(5)  # initial delay
    while True:
        trace_id = str(uuid.uuid4())
        duration_ms = round(random.uniform(5, 50), 2)
        message = f"{trace_id}|APICall|Success|timetaken={duration_ms}ms|service-a"
        await send_log(
            trace_id=trace_id,
            service_name="service-a",
            status="SUCCESS",
            message=message,
            duration_ms=duration_ms,
        )
        await asyncio.sleep(10)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(_background_log_emitter())