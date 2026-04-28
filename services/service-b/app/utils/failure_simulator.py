import asyncio
import time
from typing import Optional

from fastapi import HTTPException


async def simulate_failure(fail: Optional[str], service_name: str) -> None:
    """Simulate different failure modes based on the fail query parameter."""
    if fail is None:
        return

    if fail == "timeout":
        await asyncio.sleep(30)
        raise HTTPException(
            status_code=504,
            detail=f"{service_name} timed out after 30 seconds",
        )

    if fail == "error":
        raise HTTPException(
            status_code=500,
            detail=f"{service_name} encountered an internal error",
        )

    if fail == "high_latency":
        await asyncio.sleep(5)
        return

    if fail == "npe":
        raise HTTPException(
            status_code=500,
            detail=f"NullPointerException: {service_name} — object reference is null at processRequest()",
        )

    raise HTTPException(
        status_code=400,
        detail=f"Unknown failure mode: {fail}",
    )