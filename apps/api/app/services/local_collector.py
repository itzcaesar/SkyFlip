import asyncio
import logging
import time

from ..config import get_settings
from ..database import SessionLocal
from .collector import collect_bazaar

logger = logging.getLogger("skyflip.local_collector")


async def run_local_collector() -> None:
    """Poll Bazaar from inside the API for a simple SQLite-only development workflow."""

    settings = get_settings()
    logger.info("local_bazaar_collector_started poll_seconds=%d", settings.bazaar_poll_seconds)
    while True:
        started = time.perf_counter()
        try:
            async with SessionLocal() as session:
                result = await collect_bazaar(session, settings, redis=None)
            logger.info(
                "local_bazaar_collection_complete "
                "duration_ms=%d products=%s opportunities=%s stale=%s",
                int((time.perf_counter() - started) * 1000),
                result["products"],
                result["opportunities"],
                result["stale"],
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep the API available and let freshness make the upstream failure visible.
            logger.exception("local_bazaar_collection_failed")
        await asyncio.sleep(settings.bazaar_poll_seconds)
