from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, BazaarHistoryRollup, BazaarProduct
from app.services.history_rollups import HistoryObservation, upsert_history_rollups


@pytest.mark.asyncio
async def test_history_rollups_build_hour_and_day_candles() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    start = datetime(2026, 8, 12, 8, 15, tzinfo=UTC)
    observations = [
        HistoryObservation("TEST_ITEM", "buy_order_to_sell_order", start, 100, 110, 3, 40, 60, 1),
        HistoryObservation(
            "TEST_ITEM",
            "buy_order_to_sell_order",
            start + timedelta(minutes=10),
            105,
            115,
            2,
            80,
            70,
            2,
        ),
        HistoryObservation(
            "TEST_ITEM",
            "buy_order_to_sell_order",
            start + timedelta(days=2),
            120,
            130,
            5,
            60,
            75,
            3,
        ),
    ]

    async with session_factory() as session:
        session.add(BazaarProduct(product_id="TEST_ITEM", display_name="Test Item"))
        await session.commit()
        assert await upsert_history_rollups(session, observations) == 4
        hourly = (
            await session.scalars(
                select(BazaarHistoryRollup)
                .where(BazaarHistoryRollup.interval == "hour")
                .order_by(BazaarHistoryRollup.bucket_start)
            )
        ).all()
        daily = (
            await session.scalars(
                select(BazaarHistoryRollup)
                .where(BazaarHistoryRollup.interval == "day")
                .order_by(BazaarHistoryRollup.bucket_start)
            )
        ).all()

    await engine.dispose()
    assert len(hourly) == 2
    assert len(daily) == 2
    assert float(hourly[0].buy_open) == 100
    assert float(hourly[0].buy_high) == 105
    assert float(hourly[0].buy_close) == 105
    assert hourly[0].volume == 5
    assert hourly[0].sample_count == 2
    assert float(daily[0].sell_high) == 115
    assert daily[0].sample_count == 2
