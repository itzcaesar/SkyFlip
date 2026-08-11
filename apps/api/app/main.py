import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis

from .config import get_settings
from .database import engine, ensure_local_schema
from .dependencies import redis_dependency
from .redis_client import get_redis
from .routers import bazaar, health, items
from .services.events import redis_event_stream
from .services.local_collector import run_local_collector

logging.basicConfig(level=get_settings().log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await ensure_local_schema()
    local_collector_task = None
    if settings.local_collector_enabled and settings.database_url.startswith("sqlite"):
        local_collector_task = asyncio.create_task(run_local_collector())
        app.state.local_collector_task = local_collector_task
    yield
    if local_collector_task is not None:
        local_collector_task.cancel()
        with suppress(asyncio.CancelledError):
            await local_collector_task
    redis = get_redis()
    try:
        if redis is not None:
            await redis.aclose()
    except Exception:
        pass
    await engine.dispose()


app = FastAPI(
    title="SkyFlip API",
    version="0.1.0",
    description="Real-data market intelligence API for Hypixel SkyBlock Bazaar and Auction House.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    logging.getLogger(__name__).exception("unhandled_api_error", exc_info=exc)
    return JSONResponse(
        status_code=500, content={"detail": "The service is temporarily unavailable."}
    )


app.include_router(health.router, prefix="/api")
app.include_router(bazaar.router, prefix="/api")
app.include_router(items.router, prefix="/api")


@app.get("/api/events", tags=["live"], summary="Stream market updates over Server-Sent Events")
async def events(redis: Redis | None = Depends(redis_dependency)):
    async def stream() -> AsyncIterator[str]:
        if redis is None:
            warning = '{"message":"Redis is not configured; the local app uses polling."}'
            yield f"event: market.warning\ndata: {warning}\n\n"
            while True:
                await asyncio.sleep(15)
                yield ": keep-alive\n\n"

        try:
            async for event in redis_event_stream(redis):
                if event is None:
                    yield ": keep-alive\n\n"
                else:
                    event_type = event.get("type", "market.updated")
                    event_data = json.dumps(event)
                    yield f"event: {event_type}\ndata: {event_data}\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            warning = '{"message":"Live updates are temporarily unavailable."}'
            yield f"event: market.warning\ndata: {warning}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
