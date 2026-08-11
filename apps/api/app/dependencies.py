from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import get_session
from .redis_client import get_redis


def settings_dependency() -> Settings:
    return get_settings()


async def session_dependency() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


def redis_dependency() -> Redis | None:
    return get_redis()
