from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.dependencies import session_dependency, settings_dependency
from app.main import app
from app.models import Base, BazaarOpportunity, BazaarProduct


@pytest.fixture
def client():
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            product = BazaarProduct(
                product_id="TEST_ITEM",
                display_name="Test Item",
                last_success_at=datetime.now(UTC),
                last_source_updated_ms=1,
            )
            opportunity = BazaarOpportunity(
                product_id="TEST_ITEM",
                flip_type="buy_order_to_sell_order",
                observed_at=datetime.now(UTC),
                source_updated_ms=1,
                buy_price=100,
                sell_price=115,
                raw_spread=15,
                spread_percentage=15,
                gross_profit=15,
                estimated_fees=1,
                net_profit=14,
                roi=14,
                buy_volume=100,
                sell_volume=100,
                transaction_volume=100,
                suggested_volume=5,
                active_buy_orders=3,
                active_sell_orders=3,
                orderbook_depth=100,
                estimated_liquidity=80,
                estimated_fill_time_seconds=300,
                competition_score=20,
                volatility=None,
                short_term_momentum=None,
                capital_efficiency=70,
                manipulation_risk_score=15,
                manipulation_risk="LOW",
                confidence_score=70,
                opportunity_score=82,
                classification="Strong",
                capital_required=500,
                is_qualified=True,
                is_stale=False,
                score_breakdown={"roi": 18},
                signal_explanations=["Test fixture only"],
            )
            session.add_all([product, opportunity])
            await session.commit()

    asyncio.run(prepare())

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[session_dependency] = override_session
    app.dependency_overrides[settings_dependency] = lambda: Settings(
        database_url="sqlite+aiosqlite:///:memory:"
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_bazaar_listing_endpoint_filters_and_serializes(client):
    response = client.get("/api/bazaar/products?min_score=80&sort_by=net_profit")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["product_name"] == "Test Item"
    assert body["items"][0]["net_profit"] == 14


def test_invalid_bazaar_query_returns_validation_error(client):
    response = client.get("/api/bazaar/products?min_score=not-a-number")
    assert response.status_code == 422
