from math import floor
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import session_dependency, settings_dependency
from ..models import BazaarHistoryPoint, BazaarOpportunity, BazaarProduct
from ..schemas import (
    BazaarHistoryResponse,
    BazaarOpportunityPage,
    BazaarOpportunityResponse,
    CapitalAllocation,
    CapitalOptimizeRequest,
    CapitalOptimizeResponse,
)
from ..services.collector import get_bazaar_status

router = APIRouter(prefix="/bazaar", tags=["bazaar"])

SORT_COLUMNS = {
    "product_id": BazaarOpportunity.product_id,
    "buy_price": BazaarOpportunity.buy_price,
    "sell_price": BazaarOpportunity.sell_price,
    "net_profit": BazaarOpportunity.net_profit,
    "roi": BazaarOpportunity.roi,
    "capital_required": BazaarOpportunity.capital_required,
    "transaction_volume": BazaarOpportunity.transaction_volume,
    "estimated_liquidity": BazaarOpportunity.estimated_liquidity,
    "estimated_fill_time_seconds": BazaarOpportunity.estimated_fill_time_seconds,
    "volatility": BazaarOpportunity.volatility,
    "manipulation_risk_score": BazaarOpportunity.manipulation_risk_score,
    "confidence_score": BazaarOpportunity.confidence_score,
    "opportunity_score": BazaarOpportunity.opportunity_score,
    "observed_at": BazaarOpportunity.observed_at,
}


def _response(opportunity: BazaarOpportunity, product: BazaarProduct) -> BazaarOpportunityResponse:
    values = {
        column.name: getattr(opportunity, column.name)
        for column in BazaarOpportunity.__table__.columns
    }
    values["product_name"] = product.display_name
    return BazaarOpportunityResponse.model_validate(values)


async def _freshness(session: AsyncSession, settings: Settings):
    status = await get_bazaar_status(session, settings)
    return status["freshness"]


def _filters(
    *,
    search: str | None,
    min_profit: float | None,
    min_roi: float | None,
    max_capital: float | None,
    min_volume: int | None,
    min_liquidity: float | None,
    max_fill_time: int | None,
    risk_level: str | None,
    min_score: float | None,
    min_confidence: float | None,
    flip_type: str,
    include_stale: bool,
):
    filters = [BazaarOpportunity.flip_type == flip_type, BazaarProduct.is_active.is_(True)]
    if not include_stale:
        filters.append(BazaarOpportunity.is_stale.is_(False))
    if search:
        filters.append(BazaarProduct.display_name.ilike(f"%{search.strip()}%"))
    if min_profit is not None:
        filters.append(BazaarOpportunity.net_profit >= min_profit)
    if min_roi is not None:
        filters.append(BazaarOpportunity.roi >= min_roi)
    if max_capital is not None:
        filters.append(BazaarOpportunity.capital_required <= max_capital)
    if min_volume is not None:
        filters.append(BazaarOpportunity.transaction_volume >= min_volume)
    if min_liquidity is not None:
        filters.append(BazaarOpportunity.estimated_liquidity >= min_liquidity)
    if max_fill_time is not None:
        filters.append(BazaarOpportunity.estimated_fill_time_seconds <= max_fill_time)
    if risk_level:
        filters.append(BazaarOpportunity.manipulation_risk == risk_level.upper())
    if min_score is not None:
        filters.append(BazaarOpportunity.opportunity_score >= min_score)
    if min_confidence is not None:
        filters.append(BazaarOpportunity.confidence_score >= min_confidence)
    return filters


@router.get("/status", summary="Return Bazaar data freshness and counts")
async def status(
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await get_bazaar_status(session, settings)


@router.get(
    "/products", response_model=BazaarOpportunityPage, summary="Screen current Bazaar opportunities"
)
async def products(
    search: str | None = Query(default=None, max_length=100),
    min_profit: float | None = Query(default=None, ge=0),
    min_roi: float | None = Query(default=None, ge=-100),
    max_capital: float | None = Query(default=None, ge=0),
    min_volume: int | None = Query(default=None, ge=0),
    min_liquidity: float | None = Query(default=None, ge=0, le=100),
    max_fill_time: int | None = Query(default=None, ge=1),
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high|extreme)$"),
    min_score: float | None = Query(default=None, ge=0, le=100),
    min_confidence: float | None = Query(default=None, ge=0, le=100),
    flip_type: Literal[
        "buy_order_to_sell_order", "instant_buy_to_instant_sell"
    ] = "buy_order_to_sell_order",
    include_stale: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=250),
    sort_by: str = Query(default="opportunity_score"),
    sort_dir: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
) -> BazaarOpportunityPage:
    filters = _filters(
        search=search,
        min_profit=min_profit,
        min_roi=min_roi,
        max_capital=max_capital,
        min_volume=min_volume,
        min_liquidity=min_liquidity,
        max_fill_time=max_fill_time,
        risk_level=risk_level,
        min_score=min_score,
        min_confidence=min_confidence,
        flip_type=flip_type,
        include_stale=include_stale,
    )
    base = (
        select(BazaarOpportunity, BazaarProduct)
        .join(BazaarProduct, BazaarProduct.product_id == BazaarOpportunity.product_id)
        .where(*filters)
    )
    total = int(
        await session.scalar(
            select(func.count(BazaarOpportunity.id)).join(BazaarProduct).where(*filters)
        )
        or 0
    )
    column = SORT_COLUMNS.get(sort_by, BazaarOpportunity.opportunity_score)
    query = (
        base.order_by(asc(column) if sort_dir == "asc" else desc(column))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(query)).all()
    return BazaarOpportunityPage(
        items=[_response(opportunity, product) for opportunity, product in rows],
        page=page,
        page_size=page_size,
        total=total,
        freshness=await _freshness(session, settings),
    )


@router.get(
    "/opportunities",
    response_model=BazaarOpportunityPage,
    summary="Alias for the Bazaar opportunity screener",
)
async def opportunities(
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    # Keep the public alias intentionally small; the full filter surface lives on /products.
    return await products(session=session, settings=settings)


@router.get("/products/{product_id}", summary="Inspect one Bazaar product")
async def product_detail(
    product_id: str,
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    product = await session.get(BazaarProduct, product_id)
    if product is None:
        raise HTTPException(
            status_code=404, detail="Bazaar product was not found in observed market data."
        )
    rows = (
        await session.scalars(
            select(BazaarOpportunity)
            .where(BazaarOpportunity.product_id == product_id)
            .order_by(desc(BazaarOpportunity.opportunity_score))
        )
    ).all()
    return {
        "product_id": product.product_id,
        "product_name": product.display_name,
        "is_active": product.is_active,
        "opportunities": [_response(row, product) for row in rows],
        "freshness": await _freshness(session, settings),
    }


@router.get(
    "/products/{product_id}/history",
    response_model=BazaarHistoryResponse,
    summary="Read persisted Bazaar history",
)
async def product_history(
    product_id: str,
    flip_type: Literal[
        "buy_order_to_sell_order", "instant_buy_to_instant_sell"
    ] = "buy_order_to_sell_order",
    limit: int = Query(default=240, ge=1, le=2_000),
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
) -> BazaarHistoryResponse:
    product = await session.get(BazaarProduct, product_id)
    if product is None:
        raise HTTPException(
            status_code=404, detail="Bazaar product was not found in observed market data."
        )
    rows = (
        await session.scalars(
            select(BazaarHistoryPoint)
            .where(
                BazaarHistoryPoint.product_id == product_id,
                BazaarHistoryPoint.flip_type == flip_type,
            )
            .order_by(desc(BazaarHistoryPoint.observed_at))
            .limit(limit)
        )
    ).all()
    points = [
        {
            "observed_at": row.observed_at,
            "buy_price": float(row.buy_price),
            "sell_price": float(row.sell_price),
            "spread": float(row.spread),
            "volume": row.volume,
            "liquidity": float(row.liquidity),
            "opportunity_score": float(row.opportunity_score),
        }
        for row in reversed(rows)
    ]
    return BazaarHistoryResponse(
        product_id=product_id,
        flip_type=flip_type,
        points=points,
        freshness=await _freshness(session, settings),
    )


@router.post(
    "/capital-optimize",
    response_model=CapitalOptimizeResponse,
    summary="Build an estimated Bazaar capital allocation",
)
async def capital_optimize(
    request: CapitalOptimizeRequest,
    session: AsyncSession = Depends(session_dependency),
):
    risk_limit = {"conservative": 35, "balanced": 60, "aggressive": 80}[request.risk]
    rows = (
        await session.execute(
            select(BazaarOpportunity, BazaarProduct)
            .join(BazaarProduct, BazaarProduct.product_id == BazaarOpportunity.product_id)
            .where(
                BazaarOpportunity.flip_type == "buy_order_to_sell_order",
                BazaarOpportunity.is_stale.is_(False),
                BazaarOpportunity.is_qualified.is_(True),
                BazaarOpportunity.roi >= request.minimum_roi,
                BazaarOpportunity.estimated_liquidity >= request.minimum_liquidity,
                BazaarOpportunity.manipulation_risk_score <= risk_limit,
            )
            .order_by(desc(BazaarOpportunity.opportunity_score))
        )
    ).all()
    allocations: list[CapitalAllocation] = []
    remaining = request.available_capital
    for opportunity, product in rows:
        if len(allocations) >= request.maximum_concurrent_flips or remaining <= 0:
            break
        if request.max_fill_time_seconds is not None and (
            opportunity.estimated_fill_time_seconds is None
            or opportunity.estimated_fill_time_seconds > request.max_fill_time_seconds
        ):
            continue
        max_per_flip = request.available_capital * (0.5 if request.risk == "aggressive" else 0.35)
        target = min(remaining, max_per_flip)
        if opportunity.capital_required > 0:
            target = min(target, max(opportunity.capital_required, opportunity.buy_price))
        units = floor(target / float(opportunity.buy_price)) if opportunity.buy_price else 0
        allocation = units * float(opportunity.buy_price)
        if units <= 0 or allocation <= 0:
            continue
        allocations.append(
            CapitalAllocation(
                product_id=product.product_id,
                product_name=product.display_name,
                allocation=round(allocation, 2),
                expected_net_profit=round(units * float(opportunity.net_profit), 2),
                opportunity_score=float(opportunity.opportunity_score),
                estimated_fill_time_seconds=opportunity.estimated_fill_time_seconds,
                risk=opportunity.manipulation_risk,
            )
        )
        remaining -= allocation
    return CapitalOptimizeResponse(
        available_capital=request.available_capital,
        allocations=allocations,
        reserve=round(max(0, remaining), 2),
        projected_net_profit=round(sum(item.expected_net_profit for item in allocations), 2),
    )
