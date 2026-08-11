import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .dependencies import redis_dependency
from .redis_client import get_redis
from .routers import bazaar, health, items
from .services.events import redis_event_stream

logging.basicConfig(level=get_settings().log_level.upper())


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    try:
        await get_redis().aclose()
    except Exception:
        pass


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
async def events(redis=Depends(redis_dependency)):
    async def stream() -> AsyncIterator[str]:
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
