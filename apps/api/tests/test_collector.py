from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import Base, BazaarHistoryPoint, BazaarOpportunity, BazaarProduct, BazaarSnapshot
from app.services.collector import collect_bazaar


class FakeHypixelClient:
    def __init__(self, payload):
        self.payload = payload

    async def fetch_bazaar(self):
        return self.payload


def payload():
    return {
        "success": True,
        "lastUpdated": int(datetime.now(UTC).timestamp() * 1000),
        "products": {
            "ENCHANTED_DIAMOND": {
                "sell_summary": [{"price": 110, "amount": 900, "orders": 4}],
                "buy_summary": [{"price": 100, "amount": 800, "orders": 3}],
                "quick_status": {
                    "buyPrice": 110,
                    "sellPrice": 100,
                    "buyVolume": 1200,
                    "sellVolume": 1000,
                    "buyOrders": 6,
                    "sellOrders": 5,
                },
            }
        },
    }


async def test_collector_persists_normalized_data_and_deduplicates_snapshots():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    fake = FakeHypixelClient(payload())

    async with session_factory() as session:
        first = await collect_bazaar(session, settings, client=fake)
        second = await collect_bazaar(session, settings, client=fake)
        assert first["products"] == 1
        assert second["products"] == 1
        assert await session.scalar(select(func.count(BazaarProduct.product_id))) == 1
        assert await session.scalar(select(func.count(BazaarSnapshot.id))) == 1
        assert await session.scalar(select(func.count(BazaarOpportunity.id))) == 2
        assert await session.scalar(select(func.count(BazaarHistoryPoint.id))) == 2
    await engine.dispose()
