import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import BazaarHistoryPoint, BazaarOpportunity, BazaarProduct, BazaarSnapshot
from .alerts import refresh_watchlist_alerts
from .bazaar_engine import BazaarFeePolicy, compute_bazaar_opportunities, humanize_product_id
from .events import publish_event
from .freshness import freshness_for, utc_now
from .hypixel_client import HypixelClient
from .preferences import get_runtime_settings
from .retention import prune_local_history

logger = logging.getLogger(__name__)


def _payload_hash(payload: dict[str, Any]) -> str:
    # Hash canonical JSON so retries of an identical upstream snapshot do not create rows.
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_timestamp(payload: dict[str, Any], now: datetime) -> int:
    try:
        source_ms = int(payload.get("lastUpdated", 0))
    except (TypeError, ValueError):
        source_ms = 0
    return source_ms or int(now.timestamp() * 1000)


async def mark_bazaar_stale(session: AsyncSession) -> int:
    """Mark persisted values stale after an upstream failure.

    Values are never replaced with fakes.
    """

    products = list((await session.scalars(select(BazaarProduct))).all())
    for product in products:
        # A failed cycle must not leave the previous product set looking current. The
        # rows remain stored for history/detail inspection, but a successful cycle must
        # explicitly reactivate them before they can appear in current screens.
        product.is_active = False

    opportunities = list((await session.scalars(select(BazaarOpportunity))).all())
    for opportunity in opportunities:
        opportunity.is_stale = True
    await session.commit()
    return len(opportunities)


def _copy_result(
    opportunity: BazaarOpportunity,
    result: Any,
    *,
    observed_at: datetime,
    source_updated_ms: int,
    stale: bool,
) -> None:
    values = {
        "observed_at": observed_at,
        "source_updated_ms": source_updated_ms,
        "buy_price": result.buy_price,
        "sell_price": result.sell_price,
        "raw_spread": result.raw_spread,
        "spread_percentage": result.spread_percentage,
        "gross_profit": result.gross_profit,
        "estimated_fees": result.estimated_fees,
        "net_profit": result.net_profit,
        "roi": result.roi,
        "buy_volume": result.buy_volume,
        "sell_volume": result.sell_volume,
        "transaction_volume": result.transaction_volume,
        "suggested_volume": result.suggested_volume,
        "active_buy_orders": result.active_buy_orders,
        "active_sell_orders": result.active_sell_orders,
        "orderbook_depth": result.orderbook_depth,
        "estimated_liquidity": result.estimated_liquidity,
        "estimated_fill_time_seconds": result.estimated_fill_time_seconds,
        "competition_score": result.competition_score,
        "volatility": result.volatility,
        "short_term_momentum": result.short_term_momentum,
        "capital_efficiency": result.capital_efficiency,
        "manipulation_risk_score": result.manipulation_risk_score,
        "manipulation_risk": result.manipulation_risk,
        "confidence_score": result.confidence_score,
        "opportunity_score": result.opportunity_score,
        "classification": result.classification,
        "capital_required": result.capital_required,
        "is_qualified": result.is_qualified,
        "is_stale": stale,
        "score_breakdown": result.score_breakdown,
        "signal_explanations": result.signal_explanations,
    }
    for key, value in values.items():
        setattr(opportunity, key, value)


async def _history_prices(
    session: AsyncSession,
) -> dict[tuple[str, str], list[tuple[float, float]]]:
    rows = await session.execute(
        select(
            BazaarHistoryPoint.product_id,
            BazaarHistoryPoint.flip_type,
            BazaarHistoryPoint.buy_price,
            BazaarHistoryPoint.sell_price,
        ).order_by(BazaarHistoryPoint.observed_at)
    )
    samples: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for product_id, flip_type, buy_price, sell_price in rows.all():
        samples.setdefault((product_id, flip_type), []).append(
            (float(buy_price), float(sell_price))
        )
    return samples


async def collect_bazaar(
    session: AsyncSession,
    settings: Settings,
    *,
    client: HypixelClient | None = None,
    redis: Redis | None = None,
    payload: dict[str, Any] | None = None,
    source: str = "hypixel",
) -> dict[str, int | bool | str]:
    """Fetch, normalize, persist, and publish a Bazaar snapshot.

    The function is idempotent for an unchanged upstream payload and safe to retry after a
    worker restart. It intentionally raises on upstream failure so the worker can record a
    failed cycle and mark the last known values stale.
    """

    now = utc_now()
    effective_settings = await get_runtime_settings(session, settings)
    api_client = client or HypixelClient(settings)
    try:
        market_payload = payload if payload is not None else await api_client.fetch_bazaar()
    except Exception:
        await mark_bazaar_stale(session)
        raise

    products_payload = market_payload.get("products")
    if not isinstance(products_payload, dict) or not products_payload:
        await mark_bazaar_stale(session)
        raise ValueError("Hypixel Bazaar response contained no products.")

    if source == "demo":
        # Demo polling keeps freshness current but should not create a new history point for
        # the same deterministic catalog on every local retry.
        source_updated_ms = int(now.timestamp() * 1000)
        hash_payload = {key: value for key, value in market_payload.items() if key != "lastUpdated"}
    else:
        source_updated_ms = _source_timestamp(market_payload, now)
        hash_payload = market_payload
    payload_hash = _payload_hash(hash_payload)
    existing_snapshot = await session.scalar(
        select(BazaarSnapshot).where(BazaarSnapshot.payload_hash == payload_hash)
    )
    is_new_snapshot = existing_snapshot is None
    if existing_snapshot is None:
        session.add(
            BazaarSnapshot(
                fetched_at=now,
                source_updated_ms=source_updated_ms,
                payload_hash=payload_hash,
                product_count=len(products_payload),
                source=source,
            )
        )

    product_rows = {
        row.product_id: row for row in (await session.scalars(select(BazaarProduct))).all()
    }
    opportunity_rows = {
        (row.product_id, row.flip_type): row
        for row in (await session.scalars(select(BazaarOpportunity))).all()
    }
    history_prices = await _history_prices(session)
    fee_policy = BazaarFeePolicy(
        buy_fee_rate=effective_settings.bazaar_buy_fee_rate,
        sell_fee_rate=effective_settings.bazaar_sell_fee_rate,
    )
    source_age_seconds = max(0, int(now.timestamp() - source_updated_ms / 1000))
    source_is_stale = source_age_seconds > effective_settings.bazaar_stale_after_seconds

    # The upstream response is the current market set. Anything not revalidated by this
    # cycle is hidden from current screens until a later successful observation restores it.
    for product_row in product_rows.values():
        product_row.is_active = False
    for opportunity_row in opportunity_rows.values():
        opportunity_row.is_stale = True
        opportunity_row.is_qualified = False

    processed_products = 0
    processed_opportunities = 0
    qualified_opportunities = 0
    for product_id, product_payload in products_payload.items():
        if not isinstance(product_payload, dict):
            continue
        current_product = product_rows.get(product_id)
        if current_product is None:
            current_product = BazaarProduct(
                product_id=product_id, display_name=humanize_product_id(product_id)
            )
            product_rows[product_id] = current_product
            session.add(current_product)
        current_product.display_name = humanize_product_id(product_id)
        current_product.is_active = True
        current_product.last_source_updated_ms = source_updated_ms
        current_product.last_success_at = now
        current_product.last_payload_hash = payload_hash
        current_product.updated_at = now

        results = compute_bazaar_opportunities(
            product_id,
            product_payload,
            fee_policy=fee_policy,
            history_samples=len(history_prices.get((product_id, "buy_order_to_sell_order"), [])),
            history_prices_by_flip={
                "buy_order_to_sell_order": history_prices.get(
                    (product_id, "buy_order_to_sell_order"), []
                ),
                "instant_buy_to_instant_sell": history_prices.get(
                    (product_id, "instant_buy_to_instant_sell"), []
                ),
            },
            max_reasonable_roi_percent=effective_settings.bazaar_max_signal_roi_percent,
            max_price_ratio=effective_settings.bazaar_max_price_ratio,
        )
        if not results:
            # Keep the product identity searchable, but do not present old metrics as fresh
            # when the current upstream record lacks usable prices.
            for key, existing_opportunity in opportunity_rows.items():
                if key[0] == product_id:
                    existing_opportunity.is_stale = True
                    existing_opportunity.is_qualified = False
        for result in results:
            key = (product_id, result.flip_type)
            current_opportunity = opportunity_rows.get(key)
            if current_opportunity is None:
                current_opportunity = BazaarOpportunity(
                    product_id=product_id, flip_type=result.flip_type
                )
                opportunity_rows[key] = current_opportunity
                session.add(current_opportunity)
            _copy_result(
                current_opportunity,
                result,
                observed_at=now,
                source_updated_ms=source_updated_ms,
                stale=source_is_stale,
            )
            processed_opportunities += 1
            qualified_opportunities += int(result.is_qualified and not source_is_stale)
            if is_new_snapshot:
                session.add(
                    BazaarHistoryPoint(
                        product_id=product_id,
                        flip_type=result.flip_type,
                        observed_at=now,
                        buy_price=result.buy_price,
                        sell_price=result.sell_price,
                        spread=result.raw_spread,
                        volume=result.transaction_volume,
                        liquidity=result.estimated_liquidity,
                        opportunity_score=result.opportunity_score,
                        source_updated_ms=source_updated_ms,
                    )
                )
        processed_products += 1

    await session.commit()
    try:
        await prune_local_history(session, effective_settings, now=now)
        await refresh_watchlist_alerts(session)
    except Exception:
        # Retention and notifications are secondary to a committed market snapshot.
        logger.exception("bazaar_post_commit_maintenance_failed")
    event_payload = {
        "products": processed_products,
        "opportunities": processed_opportunities,
        "qualified_opportunities": qualified_opportunities,
        "source_updated_ms": source_updated_ms,
        "stale": source_is_stale,
    }
    await publish_event(redis, "bazaar.updated", event_payload)
    logger.info(
        "bazaar_collection_complete",
        extra={
            "records_processed": processed_products,
            "opportunities": processed_opportunities,
            "stale": source_is_stale,
        },
    )
    return {
        "products": processed_products,
        "opportunities": processed_opportunities,
        "qualified_opportunities": qualified_opportunities,
        "stale": source_is_stale,
        "payload_hash": payload_hash,
        "source": source,
    }


async def get_bazaar_status(session: AsyncSession, settings: Settings) -> dict[str, Any]:
    effective_settings = await get_runtime_settings(session, settings)
    # Only an active product set represents a currently usable snapshot. A previous
    # successful timestamp must not keep the status LIVE after a failed refresh.
    latest_success_at = await session.scalar(
        select(func.max(BazaarProduct.last_success_at)).where(BazaarProduct.is_active.is_(True))
    )
    latest_source_updated_ms = await session.scalar(
        select(func.max(BazaarProduct.last_source_updated_ms))
    )
    active_products = int(
        await session.scalar(
            select(func.count(BazaarProduct.product_id)).where(BazaarProduct.is_active.is_(True))
        )
        or 0
    )
    qualified = int(
        await session.scalar(
            select(func.count(BazaarOpportunity.id)).where(
                BazaarOpportunity.is_qualified.is_(True), BazaarOpportunity.is_stale.is_(False)
            )
        )
        or 0
    )
    latest_snapshot = await session.scalar(
        select(BazaarSnapshot).order_by(desc(BazaarSnapshot.fetched_at)).limit(1)
    )
    return {
        "freshness": freshness_for(
            latest_success_at,
            stale_after_seconds=effective_settings.bazaar_stale_after_seconds,
            source=latest_snapshot.source if latest_snapshot else None,
        ),
        "active_products": active_products,
        "qualified_opportunities": qualified,
        "last_source_updated_ms": latest_source_updated_ms,
    }
