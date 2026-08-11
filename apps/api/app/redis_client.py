from functools import lru_cache

from redis.asyncio import Redis

from .config import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def check_redis() -> tuple[bool, str | None]:
    redis = get_redis()
    try:
        await redis.ping()
        return True, None
    except Exception as exc:
        return False, type(exc).__name__
