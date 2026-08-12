import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import Base, BazaarHistoryPoint, BazaarSnapshot
from app.redis_client import check_redis
from app.services.collector import collect_bazaar, get_bazaar_status, mark_bazaar_stale
from app.services.demo_data import demo_bazaar_payload


def test_local_defaults_are_self_contained() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("sqlite+aiosqlite:///")
    assert settings.redis_url is None
    assert settings.auto_create_schema is True
    assert settings.local_demo_enabled is False
    assert "http://127.0.0.1:3000" in settings.cors_origin_list


def test_demo_payload_is_explicitly_labelled() -> None:
    payload = demo_bazaar_payload()
    assert "LOCAL DEMO DATA ONLY" in payload["_fixture_note"]
    assert len(payload["products"]) >= 5


@pytest.mark.asyncio
async def test_missing_redis_is_explicitly_optional() -> None:
    healthy, detail = await check_redis(None)
    assert healthy is False
    assert detail == "not_configured"


@pytest.mark.asyncio
async def test_demo_collection_is_visible_as_demo_source() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(_env_file=None, database_url="sqlite+aiosqlite:///:memory:")

    async with session_factory() as session:
        result = await collect_bazaar(
            session,
            settings,
            payload=demo_bazaar_payload(),
            source="demo",
        )
        repeat = await collect_bazaar(
            session,
            settings,
            payload=demo_bazaar_payload(),
            source="demo",
        )
        status = await get_bazaar_status(session, settings)
        snapshot_count = await session.scalar(select(func.count(BazaarSnapshot.id)))
        history_count = await session.scalar(select(func.count(BazaarHistoryPoint.id)))

    await engine.dispose()
    assert result["source"] == "demo"
    assert repeat["source"] == "demo"
    assert snapshot_count == 1
    assert history_count == 12
    assert status["freshness"].source == "demo"
    assert status["qualified_opportunities"] > 0


@pytest.mark.asyncio
async def test_failed_collection_cannot_remain_live() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(_env_file=None, database_url="sqlite+aiosqlite:///:memory:")

    async with session_factory() as session:
        await collect_bazaar(session, settings, payload=demo_bazaar_payload(), source="demo")
        stale_count = await mark_bazaar_stale(session)
        status = await get_bazaar_status(session, settings)

    await engine.dispose()
    assert stale_count > 0
    assert status["freshness"].status == "UNAVAILABLE"
    assert status["freshness"].source is None
    assert status["active_products"] == 0
    assert status["qualified_opportunities"] == 0
