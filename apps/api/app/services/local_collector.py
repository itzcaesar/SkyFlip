import asyncio
import logging
import time

from ..config import get_settings
from ..database import SessionLocal
from .auction_collector import collect_auction_house
from .collector import collect_bazaar
from .demo_data import demo_bazaar_payload

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
        except Exception as exc:
            # Keep the API available and let freshness make the upstream failure visible.
            logger.exception("local_bazaar_collection_failed")
            if settings.local_demo_enabled and not settings.is_production:
                try:
                    async with SessionLocal() as session:
                        result = await collect_bazaar(
                            session,
                            settings,
                            payload=demo_bazaar_payload(),
                            source="demo",
                            redis=None,
                        )
                    logger.warning(
                        "local_demo_collection_complete upstream_error=%s "
                        "products=%s opportunities=%s",
                        type(exc).__name__,
                        result["products"],
                        result["opportunities"],
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("local_demo_collection_failed")
        await asyncio.sleep(settings.bazaar_poll_seconds)


async def run_local_auction_collector() -> None:
    """Poll the public Auction House feed for the SQLite-only development workflow."""

    settings = get_settings()
    logger.info("local_auction_collector_started poll_seconds=%d", settings.auction_poll_seconds)
    while True:
        started = time.perf_counter()
        try:
            async with SessionLocal() as session:
                result = await collect_auction_house(session, settings)
            logger.info(
                "local_auction_collection_complete duration_ms=%d listings=%s items=%s",
                int((time.perf_counter() - started) * 1000),
                result["listings"],
                result["items"],
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("local_auction_collection_failed")
        await asyncio.sleep(settings.auction_poll_seconds)
