import statistics
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import AuctionListing, AuctionMarketObservation
from .auction_collector import get_auction_status

METHODOLOGY = (
    "Fair value uses trimmed current BIN comparables blended with repeated observed BIN "
    "medians. Hypixel's public feed does not expose completed-sale history."
)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _trimmed_median(prices: list[float]) -> float:
    ordered = sorted(prices)
    if len(ordered) >= 5:
        trim = max(1, int(len(ordered) * 0.1))
        ordered = ordered[trim:-trim] or ordered
    return float(statistics.median(ordered))


def _risk_and_confidence(
    prices: list[float], fair_value: float, history_points: int
) -> tuple[str, float]:
    if not prices or fair_value <= 0:
        return "HIGH", 0
    spread_percent = ((max(prices) - min(prices)) / fair_value) * 100
    confidence = min(78.0, 22.0 + len(prices) * 5.0)
    confidence += min(18.0, history_points * 3.0)
    confidence -= min(25.0, max(0.0, spread_percent - 10.0) * 0.45)
    confidence = round(max(10.0, min(96.0, confidence)), 1)
    if len(prices) < 2 or spread_percent > 40:
        risk = "HIGH"
    elif len(prices) < 5 or spread_percent > 20 or history_points < 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    return risk, confidence


def _item_key(normalized_id: str, fingerprint_hash: str) -> str:
    return f"{normalized_id}:{fingerprint_hash[:12]}"


def _history_map(rows: list[AuctionMarketObservation]) -> dict[tuple[str, str], list[float]]:
    history: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        history[(row.normalized_item_id, row.fingerprint_hash)].append(float(row.median_price))
    return history


def _market_record(
    rows: list[AuctionListing], history: list[float]
) -> dict[str, Any]:
    prices = sorted(float(row.price) for row in rows)
    current_fair = _trimmed_median(prices)
    history_fair = _trimmed_median(history) if history else current_fair
    # Keep current inventory influential so a stale historical baseline cannot make a
    # newly repriced item look like an enormous discount.
    fair_value = (
        (current_fair * 0.65) + (history_fair * 0.35) if history else current_fair
    )
    risk, confidence = _risk_and_confidence(prices, fair_value, len(history))
    # Do not surface a dramatic "discount" when the comparable spread is already
    # classified as high risk; those are usually stale or malformed listings, not safe
    # opportunities to buy.
    best_discount = (
        ((fair_value - prices[0]) / fair_value) * 100
        if fair_value and risk != "HIGH"
        else None
    )
    latest_seen: datetime | None = None
    for row in rows:
        candidate = _aware(row.last_seen_at)
        if candidate is not None and (latest_seen is None or candidate > latest_seen):
            latest_seen = candidate
    representative = rows[0]
    return {
        "item_key": _item_key(representative.normalized_item_id, representative.fingerprint_hash),
        "item_name": representative.item_name,
        "normalized_item_id": representative.normalized_item_id,
        "fingerprint_hash": representative.fingerprint_hash,
        "category": representative.category,
        "tier": representative.tier,
        "listings": len(prices),
        "low_bin": prices[0],
        "median_bin": float(statistics.median(prices)),
        "high_bin": prices[-1],
        "fair_value": round(fair_value, 2),
        "best_discount_percent": round(best_discount, 2) if best_discount is not None else None,
        "history_points": len(history),
        "comparable_count": len(prices),
        "confidence": confidence,
        "risk": risk,
        "updated_at": latest_seen or _now(),
    }


async def _active_rows(
    session: AsyncSession,
    *,
    normalized_id: str | None = None,
    fingerprint_prefix: str | None = None,
) -> list[AuctionListing]:
    now = _now()
    query = select(AuctionListing).where(
        AuctionListing.is_active.is_(True),
        AuctionListing.is_bin.is_(True),
        (AuctionListing.end_at.is_(None) | (AuctionListing.end_at >= now)),
    )
    if normalized_id:
        query = query.where(AuctionListing.normalized_item_id == normalized_id)
    if fingerprint_prefix:
        query = query.where(AuctionListing.fingerprint_hash.like(f"{fingerprint_prefix}%"))
    rows = (await session.scalars(query.order_by(AuctionListing.price.asc()))).all()
    return list(rows)


async def _recent_observations(
    session: AsyncSession,
    settings: Settings,
    *,
    normalized_id: str | None = None,
    fingerprint_prefix: str | None = None,
) -> list[AuctionMarketObservation]:
    cutoff = _now() - timedelta(days=settings.auction_history_retention_days)
    query = select(AuctionMarketObservation).where(
        AuctionMarketObservation.observed_at >= cutoff
    )
    if normalized_id:
        query = query.where(AuctionMarketObservation.normalized_item_id == normalized_id)
    if fingerprint_prefix:
        query = query.where(
            AuctionMarketObservation.fingerprint_hash.like(f"{fingerprint_prefix}%")
        )
    rows = (
        await session.scalars(
            query.order_by(desc(AuctionMarketObservation.observed_at)).limit(100_000)
        )
    ).all()
    return list(rows)


async def list_auction_market(
    session: AsyncSession,
    settings: Settings,
    *,
    search: str = "",
    category: str = "",
    tier: str = "",
    sort_by: str = "discount",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    rows = await _active_rows(session)
    observations = await _recent_observations(session, settings)
    history = _history_map(observations)
    grouped: dict[tuple[str, str], list[AuctionListing]] = defaultdict(list)
    for row in rows:
        grouped[(row.normalized_item_id, row.fingerprint_hash)].append(row)
    search_term = search.strip().lower()
    records = []
    for key, group in grouped.items():
        record = _market_record(group, history.get(key, []))
        if search_term and search_term not in record["item_name"].lower():
            continue
        if category and record["category"] != category.lower():
            continue
        if tier and record["tier"] != tier.upper():
            continue
        records.append(record)
    reverse = sort_dir.lower() != "asc"
    sort_keys = {
        "price": lambda item: item["low_bin"],
        "listings": lambda item: item["listings"],
        "confidence": lambda item: item["confidence"],
        "discount": lambda item: item["best_discount_percent"]
        if item["best_discount_percent"] is not None
        else -10_000,
    }
    records.sort(key=sort_keys.get(sort_by, sort_keys["discount"]), reverse=reverse)
    total = len(records)
    start = (page - 1) * page_size
    status = await get_auction_status(session, settings)
    return {
        "items": records[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "freshness": status["freshness"],
        "methodology": METHODOLOGY,
    }


async def list_auction_listings(
    session: AsyncSession,
    settings: Settings,
    *,
    search: str = "",
    item_key: str = "",
    category: str = "",
    tier: str = "",
    sort_by: str = "price",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    normalized_id: str | None = None
    fingerprint_prefix: str | None = None
    if item_key and ":" in item_key:
        normalized_id, fingerprint_prefix = item_key.split(":", 1)
    rows = await _active_rows(
        session,
        normalized_id=normalized_id,
        fingerprint_prefix=fingerprint_prefix,
    )
    observations = await _recent_observations(
        session,
        settings,
        normalized_id=normalized_id,
        fingerprint_prefix=fingerprint_prefix,
    )
    history = _history_map(observations)
    grouped: dict[tuple[str, str], list[AuctionListing]] = defaultdict(list)
    for row in rows:
        grouped[(row.normalized_item_id, row.fingerprint_hash)].append(row)
    market = {
        key: _market_record(group, history.get(key, [])) for key, group in grouped.items()
    }
    search_term = search.strip().lower()
    filtered: list[dict[str, Any]] = []
    for row in rows:
        key = (row.normalized_item_id, row.fingerprint_hash)
        valuation = market[key]
        if item_key and valuation["item_key"] != item_key:
            continue
        if search_term and search_term not in row.item_name.lower():
            continue
        if category and row.category != category.lower():
            continue
        if tier and row.tier != tier.upper():
            continue
        fair_value = float(valuation["fair_value"])
        discount = ((fair_value - float(row.price)) / fair_value) * 100 if fair_value else None
        filtered.append(
            {
                "auction_uuid": row.auction_uuid,
                "item_uuid": row.item_uuid,
                "item_name": row.item_name,
                "normalized_item_id": row.normalized_item_id,
                "fingerprint_hash": row.fingerprint_hash,
                "category": row.category,
                "tier": row.tier,
                "price": float(row.price),
                "fair_value": fair_value,
                "discount_percent": round(discount, 2) if discount is not None else None,
                "confidence": valuation["confidence"],
                "risk": valuation["risk"],
                "end_at": _aware(row.end_at),
                "last_seen_at": _aware(row.last_seen_at) or _now(),
            }
        )
    key_getters = {
        "price": lambda item: item["price"],
        "discount": lambda item: item["discount_percent"]
        if item["discount_percent"] is not None
        else -10_000,
        "ending": lambda item: item["end_at"] or datetime.max.replace(tzinfo=UTC),
    }
    filtered.sort(
        key=key_getters.get(sort_by, key_getters["price"]),
        reverse=sort_dir.lower() != "asc",
    )
    total = len(filtered)
    start = (page - 1) * page_size
    status = await get_auction_status(session, settings)
    return {
        "items": filtered[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "freshness": status["freshness"],
    }
