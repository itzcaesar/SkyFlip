import asyncio
import logging
import time
from contextlib import suppress

from app.config import get_settings
from app.database import SessionLocal, ensure_local_schema
from app.redis_client import get_redis
from app.services.collector import collect_bazaar

logging.basicConfig(
    level=get_settings().log_level.upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("skyflip.worker")


async def run_cycle() -> None:
    settings = get_settings()
    redis = get_redis()
    lock = None
    acquired = redis is None
    started = time.perf_counter()
    try:
        if redis is not None:
            lock = redis.lock(
                "skyflip:lock:bazaar-collector",
                timeout=max(settings.bazaar_poll_seconds * 2, 60),
            )
            with suppress(Exception):
                await redis.set(
                    "skyflip:worker:heartbeat",
                    "alive",
                    ex=max(settings.bazaar_poll_seconds * 3, 90),
                )
            acquired = await lock.acquire(blocking=False)
            if not acquired:
                logger.info("bazaar_cycle_skipped_lock_held")
                return
        async with SessionLocal() as session:
            result = await collect_bazaar(session, settings, redis=redis)
        logger.info(
            "bazaar_cycle_complete duration_ms=%d products=%s opportunities=%s stale=%s",
            int((time.perf_counter() - started) * 1000),
            result["products"],
            result["opportunities"],
            result["stale"],
        )
        if redis is not None:
            with suppress(Exception):
                await redis.set(
                    "skyflip:worker:last-success", str(int(time.time())), ex=86_400
                )
    except Exception:
        logger.exception("bazaar_cycle_failed")
        if redis is not None:
            with suppress(Exception):
                await redis.set(
                    "skyflip:worker:last-failure", str(int(time.time())), ex=86_400
                )
    finally:
        if acquired and lock is not None:
            with suppress(Exception):
                await lock.release()


async def main() -> None:
    settings = get_settings()
    await ensure_local_schema()
    logger.info("skyflip_worker_started poll_seconds=%d", settings.bazaar_poll_seconds)
    while True:
        await run_cycle()
        await asyncio.sleep(settings.bazaar_poll_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("skyflip_worker_stopped")
