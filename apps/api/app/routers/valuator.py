from statistics import median, pstdev

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import session_dependency, settings_dependency
from ..models import BazaarHistoryPoint, BazaarOpportunity, BazaarProduct
from ..schemas import ItemValuationResponse
from ..services.collector import get_bazaar_status

router = APIRouter(prefix="/valuator", tags=["valuator"])


@router.get(
    "", response_model=ItemValuationResponse, summary="Estimate value from observed Bazaar history"
)
async def valuate_item(
    product_id: str = Query(min_length=1, max_length=96),
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    product = await session.get(BazaarProduct, product_id.upper())
    if product is None:
        raise HTTPException(
            status_code=404, detail="That item has not been observed in Bazaar data."
        )
    opportunities = (
        await session.scalars(
            select(BazaarOpportunity)
            .where(BazaarOpportunity.product_id == product.product_id)
            .order_by(desc(BazaarOpportunity.observed_at))
        )
    ).all()
    order = next(
        (row for row in opportunities if row.flip_type == "buy_order_to_sell_order"), None
    )
    instant = next(
        (row for row in opportunities if row.flip_type == "instant_buy_to_instant_sell"), None
    )
    history_rows = (
        await session.scalars(
            select(BazaarHistoryPoint)
            .where(
                BazaarHistoryPoint.product_id == product.product_id,
                BazaarHistoryPoint.flip_type == "buy_order_to_sell_order",
            )
            .order_by(desc(BazaarHistoryPoint.observed_at))
            .limit(240)
        )
    ).all()
    sell_prices = [float(row.sell_price) for row in reversed(history_rows) if row.sell_price > 0]
    returns = [
        (current - previous) / previous * 100
        for previous, current in zip(sell_prices, sell_prices[1:], strict=False)
        if previous > 0
    ]
    status = await get_bazaar_status(session, settings)
    return {
        "product_id": product.product_id,
        "product_name": product.display_name,
        "freshness": status["freshness"],
        "current_buy_order": float(order.buy_price) if order else None,
        "current_sell_order": float(order.sell_price) if order else None,
        "instant_buy_price": float(instant.buy_price) if instant else None,
        "instant_sell_price": float(instant.sell_price) if instant else None,
        "observed_low": min(sell_prices) if sell_prices else None,
        "observed_high": max(sell_prices) if sell_prices else None,
        "observed_median": median(sell_prices) if sell_prices else None,
        "price_change_percent": (
            round((sell_prices[-1] / sell_prices[0] - 1) * 100, 2)
            if len(sell_prices) >= 2 and sell_prices[0] > 0
            else None
        ),
        "volatility_percent": round(min(100, pstdev(returns)), 2) if returns else None,
        "liquidity": float(order.estimated_liquidity) if order else None,
        "confidence": float(order.confidence_score) if order else None,
        "risk": order.manipulation_risk if order else None,
        "history_points": len(sell_prices),
    }
