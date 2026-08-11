from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..database import check_database
from ..dependencies import redis_dependency, session_dependency, settings_dependency
from ..redis_client import check_redis
from ..schemas import HealthComponent, HealthResponse
from ..services.collector import get_bazaar_status

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Inspect service and market health")
async def health(
    session: AsyncSession = Depends(session_dependency),
    redis: Redis = Depends(redis_dependency),
    settings: Settings = Depends(settings_dependency),
) -> HealthResponse:
    db_ok, db_detail = await check_database()
    redis_ok, redis_detail = await check_redis()
    worker_ok = False
    worker_detail: str | None = "No worker heartbeat has been observed."
    if redis_ok:
        try:
            heartbeat = await redis.get("skyflip:worker:heartbeat")
            worker_ok = heartbeat is not None
            worker_detail = None if worker_ok else worker_detail
        except Exception as exc:
            worker_detail = type(exc).__name__
    try:
        bazaar_status = await get_bazaar_status(session, settings)
        bazaar_state = bazaar_status["freshness"].status.lower()
        bazaar_ok = bazaar_state in {"live", "delayed"}
        bazaar_component = HealthComponent(
            status="ok"
            if bazaar_ok
            else "unavailable"
            if bazaar_state == "unavailable"
            else "degraded",
            detail=bazaar_status["freshness"].message,
        )
    except Exception as exc:
        bazaar_component = HealthComponent(status="unavailable", detail=type(exc).__name__)

    component_statuses = [db_ok, redis_ok, worker_ok, bazaar_component.status == "ok"]
    overall: Literal["ok", "degraded", "unavailable"] = (
        "ok"
        if all(component_statuses)
        else "degraded"
        if any(component_statuses)
        else "unavailable"
    )
    return HealthResponse(
        status=overall,
        service="skyflip-api",
        database=HealthComponent(status="ok" if db_ok else "unavailable", detail=db_detail),
        redis=HealthComponent(status="ok" if redis_ok else "unavailable", detail=redis_detail),
        worker=HealthComponent(status="ok" if worker_ok else "degraded", detail=worker_detail),
        bazaar=bazaar_component,
        checked_at=datetime.now(UTC),
    )
