from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import session_dependency
from ..models import BazaarOpportunity, BazaarProduct, WatchlistItem
from ..schemas import (
    AlertPreferencesResponse,
    AlertPreferencesUpdate,
    AlertResponse,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistUpdate,
)
from ..services.alert_preferences import get_alert_preferences, update_alert_preferences
from ..services.alerts import (
    list_alerts,
    mark_alert_read,
    mark_all_alerts_read,
    refresh_watchlist_alerts,
)

router = APIRouter(tags=["alerts"])


def _opportunity_response(opportunity: BazaarOpportunity, product: BazaarProduct) -> dict:
    values = {
        column.name: getattr(opportunity, column.name)
        for column in BazaarOpportunity.__table__.columns
    }
    values["product_name"] = product.display_name
    return values


async def _watchlist_response(
    session: AsyncSession, item: WatchlistItem, product: BazaarProduct
) -> dict:
    opportunity = await session.scalar(
        select(BazaarOpportunity)
        .where(
            BazaarOpportunity.product_id == item.product_id,
            BazaarOpportunity.flip_type == item.flip_type,
            BazaarOpportunity.is_stale.is_(False),
            BazaarOpportunity.is_qualified.is_(True),
        )
        .order_by(desc(BazaarOpportunity.observed_at))
        .limit(1)
    )
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": product.display_name,
        "flip_type": item.flip_type,
        "min_score": float(item.min_score),
        "min_profit": float(item.min_profit),
        "min_roi": float(item.min_roi),
        "is_active": item.is_active,
        "created_at": item.created_at,
        "current_opportunity": _opportunity_response(opportunity, product)
        if opportunity is not None
        else None,
    }


@router.get("/alerts", response_model=list[AlertResponse], summary="List local market alerts")
async def alerts(
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=250),
    session: AsyncSession = Depends(session_dependency),
):
    return await list_alerts(session, unread_only=unread_only, limit=limit)


@router.post("/alerts/{alert_id}/read", response_model=AlertResponse)
async def read_alert(alert_id: int, session: AsyncSession = Depends(session_dependency)):
    result = await mark_alert_read(session, alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Alert was not found.")
    return result


@router.post("/alerts/read-all", summary="Mark every local alert as read")
async def read_all_alerts(session: AsyncSession = Depends(session_dependency)):
    return {"marked_read": await mark_all_alerts_read(session)}


@router.get(
    "/alerts/preferences",
    response_model=AlertPreferencesResponse,
    summary="Read local alert delivery preferences",
)
async def alert_preferences(session: AsyncSession = Depends(session_dependency)):
    return await get_alert_preferences(session)


@router.patch(
    "/alerts/preferences",
    response_model=AlertPreferencesResponse,
    summary="Update local alert delivery preferences",
)
async def patch_alert_preferences(
    payload: AlertPreferencesUpdate,
    session: AsyncSession = Depends(session_dependency),
):
    return await update_alert_preferences(session, payload.model_dump(exclude_none=True))


@router.get(
    "/watchlist", response_model=list[WatchlistResponse], summary="List the local Bazaar watchlist"
)
async def watchlist(
    include_inactive: bool = False,
    session: AsyncSession = Depends(session_dependency),
):
    query = (
        select(WatchlistItem, BazaarProduct)
        .join(BazaarProduct, WatchlistItem.product_id == BazaarProduct.product_id)
        .order_by(desc(WatchlistItem.created_at))
    )
    if not include_inactive:
        query = query.where(WatchlistItem.is_active.is_(True))
    rows = (await session.execute(query)).all()
    return [await _watchlist_response(session, item, product) for item, product in rows]


@router.post("/watchlist", response_model=WatchlistResponse)
async def add_watchlist_item(
    payload: WatchlistCreate,
    session: AsyncSession = Depends(session_dependency),
):
    product = await session.get(BazaarProduct, payload.product_id.upper())
    if product is None:
        raise HTTPException(
            status_code=404, detail="That item has not been observed in Bazaar data."
        )
    item = await session.scalar(
        select(WatchlistItem).where(
            WatchlistItem.product_id == product.product_id,
            WatchlistItem.flip_type == payload.flip_type,
        )
    )
    if item is None:
        item = WatchlistItem(product_id=product.product_id, flip_type=payload.flip_type)
        session.add(item)
    item.min_score = Decimal(str(payload.min_score))
    item.min_profit = Decimal(str(payload.min_profit))
    item.min_roi = Decimal(str(payload.min_roi))
    item.is_active = True
    await session.commit()
    await refresh_watchlist_alerts(session)
    return await _watchlist_response(session, item, product)


@router.patch("/watchlist/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist_item(
    watchlist_id: int,
    payload: WatchlistUpdate,
    session: AsyncSession = Depends(session_dependency),
):
    item = await session.get(WatchlistItem, watchlist_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Watchlist item was not found.")
    product = await session.get(BazaarProduct, item.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="The watched Bazaar item was not found.")
    updates = payload.model_dump(exclude_none=True)
    for key in ("min_score", "min_profit", "min_roi"):
        if key in updates:
            setattr(item, key, Decimal(str(updates[key])))
    if "is_active" in updates:
        item.is_active = bool(updates["is_active"])
    await session.commit()
    await refresh_watchlist_alerts(session)
    return await _watchlist_response(session, item, product)


@router.delete("/watchlist/{watchlist_id}", summary="Remove an item from the local watchlist")
async def remove_watchlist_item(
    watchlist_id: int, session: AsyncSession = Depends(session_dependency)
):
    item = await session.get(WatchlistItem, watchlist_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Watchlist item was not found.")
    await session.delete(item)
    await session.commit()
    return {"removed": watchlist_id}
