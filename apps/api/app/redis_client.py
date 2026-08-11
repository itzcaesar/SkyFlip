from functools import lru_cache

from redis.asyncio import Redis

from .config import get_settings


@lru_cache
def get_redis() -> Redis | None:
    redis_url = get_settings().redis_url
    if not redis_url:
        return None
    return Redis.from_url(redis_url, decode_responses=True)


async def check_redis(redis: Redis | None = None) -> tuple[bool, str | None]:
    redis = redis if redis is not None else get_redis()
    if redis is None:
        return False, "not_configured"
    try:
        await redis.ping()
        return True, None
    except Exception as exc:
        return False, type(exc).__name__
