from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AlertEvent, BazaarOpportunity, BazaarProduct, WatchlistItem
from .alert_preferences import get_alert_preferences


def _alert_payload(row: AlertEvent) -> dict:
    return {
        "id": row.id,
        "market": row.market,
        "item_key": row.item_key,
        "alert_type": row.alert_type,
        "severity": row.severity,
        "description": row.description,
        "estimated_profit": (
            float(row.estimated_profit) if row.estimated_profit is not None else None
        ),
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "risk": row.risk,
        "is_read": row.is_read,
        "created_at": row.created_at,
    }


async def list_alerts(
    session: AsyncSession, *, unread_only: bool = False, limit: int = 100
) -> list[dict]:
    query = select(AlertEvent).order_by(desc(AlertEvent.created_at)).limit(limit)
    if unread_only:
        query = query.where(AlertEvent.is_read.is_(False))
    rows = (await session.scalars(query)).all()
    return [_alert_payload(row) for row in rows]


async def mark_alert_read(session: AsyncSession, alert_id: int) -> dict | None:
    row = await session.get(AlertEvent, alert_id)
    if row is None:
        return None
    row.is_read = True
    await session.commit()
    return _alert_payload(row)


async def mark_all_alerts_read(session: AsyncSession) -> int:
    rows = (await session.scalars(select(AlertEvent).where(AlertEvent.is_read.is_(False)))).all()
    for row in rows:
        row.is_read = True
    await session.commit()
    return len(rows)


async def refresh_watchlist_alerts(session: AsyncSession) -> int:
    """Create a throttled alert when a watched item crosses its local threshold."""

    preferences = await get_alert_preferences(session)
    if not bool(preferences["enabled"]):
        return 0
    severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    minimum_severity = str(preferences["minimum_severity"])
    cooldown_minutes = int(preferences["cooldown_minutes"])
    rows = (
        await session.execute(
            select(WatchlistItem, BazaarProduct, BazaarOpportunity)
            .join(BazaarProduct, WatchlistItem.product_id == BazaarProduct.product_id)
            .join(
                BazaarOpportunity,
                and_(
                    BazaarOpportunity.product_id == WatchlistItem.product_id,
                    BazaarOpportunity.flip_type == WatchlistItem.flip_type,
                ),
            )
            .where(
                WatchlistItem.is_active.is_(True),
                BazaarProduct.is_active.is_(True),
                BazaarOpportunity.is_stale.is_(False),
                BazaarOpportunity.is_qualified.is_(True),
                BazaarOpportunity.opportunity_score >= WatchlistItem.min_score,
                BazaarOpportunity.net_profit >= WatchlistItem.min_profit,
                BazaarOpportunity.roi >= WatchlistItem.min_roi,
            )
        )
    ).all()
    now = datetime.now(UTC)
    created = 0
    for watchlist, product, opportunity in rows:
        item_key = f"{product.product_id}:{watchlist.flip_type}"
        last = await session.scalar(
            select(AlertEvent)
            .where(
                AlertEvent.item_key == item_key,
                AlertEvent.alert_type == "watchlist_signal",
            )
            .order_by(desc(AlertEvent.created_at))
            .limit(1)
        )
        if last is not None and last.created_at is not None:
            last_created = last.created_at
            if last_created.tzinfo is None:
                last_created = last_created.replace(tzinfo=UTC)
            if now - last_created < timedelta(minutes=cooldown_minutes):
                continue
        severity = "HIGH" if float(opportunity.opportunity_score) >= 90 else "MEDIUM"
        if severity_rank[severity] < severity_rank[minimum_severity]:
            continue
        session.add(
            AlertEvent(
                market="bazaar",
                item_key=item_key,
                alert_type="watchlist_signal",
                severity=severity,
                description=(
                    f"{product.display_name} reached "
                    f"{float(opportunity.opportunity_score):.0f}/100 "
                    f"with {float(opportunity.net_profit):,.0f} coins net per unit."
                ),
                estimated_profit=opportunity.net_profit,
                confidence=opportunity.confidence_score,
                risk=opportunity.manipulation_risk,
                is_read=False,
            )
        )
        created += 1
    if created:
        await session.commit()
    return created
