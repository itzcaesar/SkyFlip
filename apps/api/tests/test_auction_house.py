from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import AuctionListing, AuctionMarketObservation, Base
from app.services.auction_collector import collect_auction_house
from app.services.auction_valuation import list_auction_listings, list_auction_market


def _payload() -> dict:
    now = int(datetime.now(UTC).timestamp() * 1000)
    common = {
        "item_name": "§aTest Sword",
        "item_lore": "§9§lRARE SWORD",
        "extra": "Test Sword Diamond Sword",
        "category": "weapon",
        "tier": "RARE",
        "start": now - 1_000,
        "end": now + 3_600_000,
        "bin": True,
        "claimed": False,
    }
    return {
        "success": True,
        "lastUpdated": now,
        "totalPages": 1,
        "pageCount": 1,
        "totalAuctions": 3,
        "auctions": [
            {**common, "uuid": "a" * 32, "item_uuid": "i" * 32, "starting_bid": 1_000},
            {**common, "uuid": "b" * 32, "item_uuid": "j" * 32, "starting_bid": 1_500},
            {
                "uuid": "c" * 32,
                "item_name": "Bid Only",
                "starting_bid": 900,
                "bin": False,
                "claimed": False,
            },
        ],
    }


@pytest.mark.asyncio
async def test_auction_collection_normalizes_bins_and_is_idempotent() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(_env_file=None, database_url="sqlite+aiosqlite:///:memory:")
    payload = _payload()

    async with session_factory() as session:
        first = await collect_auction_house(session, settings, payload=payload)
        second = await collect_auction_house(session, settings, payload=payload)
        market = await list_auction_market(session, settings)
        listings = await list_auction_listings(session, settings)
        listing_count = await session.scalar(select(func.count(AuctionListing.id)))
        observation_count = await session.scalar(
            select(func.count(AuctionMarketObservation.id))
        )

    await engine.dispose()
    assert first["listings"] == 2
    assert second["new_snapshot"] is False
    assert listing_count == 2
    assert observation_count == 1
    assert market["total"] == 1
    assert market["items"][0]["fair_value"] == 1_250
    assert listings["total"] == 2
