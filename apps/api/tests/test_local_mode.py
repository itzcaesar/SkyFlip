import pytest

from app.config import Settings
from app.redis_client import check_redis


def test_local_defaults_are_self_contained() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("sqlite+aiosqlite:///")
    assert settings.redis_url is None
    assert settings.auto_create_schema is True


@pytest.mark.asyncio
async def test_missing_redis_is_explicitly_optional() -> None:
    healthy, detail = await check_redis(None)
    assert healthy is False
    assert detail == "not_configured"
