import hashlib
import json
import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import distinct, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import AuctionHouseSnapshot, AuctionListing, AuctionMarketObservation
from .auction_parser import parse_auction
from .freshness import freshness_for, utc_now
from .hypixel_client import HypixelClient
from .retention import prune_local_history

logger = logging.getLogger(__name__)


def _payload_hash(payload: dict[str, Any], source_updated_ms: int) -> str:
    identity = {
        "lastUpdated": source_updated_ms,
        "totalPages": payload.get("totalPages"),
        "pageCount": payload.get("pageCount"),
        "totalAuctions": payload.get("totalAuctions"),
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _source_timestamp(payload: dict[str, Any], now: datetime) -> int:
    try:
        source_ms = int(payload.get("lastUpdated", 0))
    except (TypeError, ValueError):
        source_ms = 0
    return source_ms or int(now.timestamp() * 1000)


def _chunks(values: list[str], size: int = 500):
    for index in range(0, len(values), size):
        yield values[index : index + size]


async def _current_listing_rows(
    session: AsyncSession, auction_uuids: list[str]
) -> dict[str, AuctionListing]:
    rows: dict[str, AuctionListing] = {}
    for chunk in _chunks(auction_uuids):
        result = await session.scalars(
            select(AuctionListing).where(AuctionListing.auction_uuid.in_(chunk))
        )
        for row in result.all():
            rows[row.auction_uuid] = row
    return rows


async def _upsert_sqlite_listings(
    session: AsyncSession,
    records: list[dict[str, Any]],
    *,
    now: datetime,
    source_updated_ms: int,
    payload_hash: str,
) -> None:
    update_fields = (
        "item_uuid",
        "item_name",
        "normalized_item_id",
        "fingerprint_hash",
        "item_fingerprint",
        "item_lore",
        "extra",
        "category",
        "tier",
        "price",
        "is_bin",
        "is_claimed",
        "start_at",
        "end_at",
        "is_active",
        "last_seen_at",
        "last_source_updated_ms",
        "last_snapshot_hash",
    )
    for index in range(0, len(records), 500):
        chunk_records = records[index : index + 500]
        values = [
            {
                **record,
                "first_seen_at": now,
                "last_seen_at": now,
                "last_source_updated_ms": source_updated_ms,
                "last_snapshot_hash": payload_hash,
            }
            for record in chunk_records
        ]
        statement = sqlite_insert(AuctionListing).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=["auction_uuid"],
            set_={
                field: getattr(statement.excluded, field)
                for field in update_fields
            },
        )
        await session.execute(statement)
        await session.commit()


async def _upsert_sqlite_observations(
    session: AsyncSession, observations: list[dict[str, Any]]
) -> None:
    for index in range(0, len(observations), 500):
        statement = sqlite_insert(AuctionMarketObservation).values(
            observations[index : index + 500]
        )
        statement = statement.on_conflict_do_nothing(
            index_elements=["normalized_item_id", "fingerprint_hash", "source_updated_ms"]
        )
        await session.execute(statement)
    await session.commit()


async def _recent_observation_keys(
    session: AsyncSession, settings: Settings, now: datetime
) -> set[tuple[str, str]]:
    cutoff = now - timedelta(seconds=settings.auction_observation_interval_seconds)
    rows = await session.execute(
        select(
            AuctionMarketObservation.normalized_item_id,
            AuctionMarketObservation.fingerprint_hash,
        ).where(AuctionMarketObservation.observed_at >= cutoff)
    )
    return {(str(row[0]), str(row[1])) for row in rows.all()}


def _group_prices(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"records": [], "prices": []}
    )
    for record in records:
        key = (record["normalized_item_id"], record["fingerprint_hash"])
        groups[key]["records"].append(record)
        groups[key]["prices"].append(record["price"])
    return groups


async def collect_auction_house(
    session: AsyncSession,
    settings: Settings,
    *,
    client: HypixelClient | None = None,
    payload: dict[str, Any] | None = None,
    source: str = "hypixel",
) -> dict[str, int | bool | str]:
    """Fetch and persist current BIN listings and compact comparable observations."""

    now = utc_now()
    api_client = client or HypixelClient(settings)
    market_payload = payload if payload is not None else await api_client.fetch_auctions()
    raw_auctions = market_payload.get("auctions")
    if not isinstance(raw_auctions, list):
        raise ValueError("Hypixel Auction House response contained no auctions list.")
    source_updated_ms = _source_timestamp(market_payload, now)
    payload_hash = _payload_hash(market_payload, source_updated_ms)
    existing_snapshot = await session.scalar(
        select(AuctionHouseSnapshot).where(AuctionHouseSnapshot.payload_hash == payload_hash)
    )
    is_new_snapshot = existing_snapshot is None
    parsed = [record for raw in raw_auctions if (record := parse_auction(raw)) is not None]
    if settings.database_url.startswith("sqlite"):
        await _upsert_sqlite_listings(
            session,
            parsed,
            now=now,
            source_updated_ms=source_updated_ms,
            payload_hash=payload_hash,
        )
    else:
        auction_uuids = [record["auction_uuid"] for record in parsed]
        rows_by_uuid = await _current_listing_rows(session, auction_uuids)
        for record in parsed:
            row = rows_by_uuid.get(record["auction_uuid"])
            if row is None:
                row = AuctionListing(
                    auction_uuid=record["auction_uuid"],
                    first_seen_at=now,
                )
                session.add(row)
                rows_by_uuid[record["auction_uuid"]] = row
            for key, value in record.items():
                setattr(row, key, value)
            row.is_active = True
            row.last_seen_at = now
            row.last_source_updated_ms = source_updated_ms
            row.last_snapshot_hash = payload_hash

    # Only hide the previous set after the new page sweep has been written. If a network
    # or SQLite error interrupts the upsert, the last complete set remains queryable.
    await session.execute(
        update(AuctionListing)
        .where(
            AuctionListing.is_active.is_(True),
            AuctionListing.last_snapshot_hash != payload_hash,
        )
        .values(is_active=False)
    )
    await session.commit()

    if existing_snapshot is None:
        session.add(
            AuctionHouseSnapshot(
                fetched_at=now,
                source_updated_ms=source_updated_ms,
                payload_hash=payload_hash,
                page_count=int(
                    market_payload.get("pageCount", market_payload.get("totalPages", 1))
                ),
                auction_count=len(raw_auctions),
                bin_count=len(parsed),
                source=source,
            )
        )

    if is_new_snapshot:
        recent_keys = await _recent_observation_keys(session, settings, now)
        observation_values: list[dict[str, Any]] = []
        for (normalized_id, fingerprint_hash), group in _group_prices(parsed).items():
            if (normalized_id, fingerprint_hash) in recent_keys:
                continue
            prices = sorted(float(price) for price in group["prices"])
            representative = group["records"][0]
            observation_values.append(
                {
                    "observed_at": now,
                    "source_updated_ms": source_updated_ms,
                    "snapshot_hash": payload_hash,
                    "normalized_item_id": normalized_id,
                    "fingerprint_hash": fingerprint_hash,
                    "item_name": representative["item_name"],
                    "category": representative["category"],
                    "tier": representative["tier"],
                    "listing_count": len(prices),
                    "low_price": prices[0],
                    "median_price": statistics.median(prices),
                    "high_price": prices[-1],
                }
            )
        if settings.database_url.startswith("sqlite"):
            await _upsert_sqlite_observations(session, observation_values)
        else:
            session.add_all(
                [AuctionMarketObservation(**values) for values in observation_values]
            )

    await session.commit()
    await prune_local_history(session, settings, now=now)
    logger.info(
        "auction_collection_complete listings=%d raw_auctions=%d new_snapshot=%s",
        len(parsed),
        len(raw_auctions),
        is_new_snapshot,
    )
    return {
        "listings": len(parsed),
        "auctions": len(raw_auctions),
        "items": len(_group_prices(parsed)),
        "new_snapshot": is_new_snapshot,
        "payload_hash": payload_hash,
        "source": source,
    }


async def get_auction_status(session: AsyncSession, settings: Settings) -> dict[str, Any]:
    latest_snapshot = await session.scalar(
        select(AuctionHouseSnapshot)
        .order_by(AuctionHouseSnapshot.fetched_at.desc())
        .limit(1)
    )
    active_count = int(
        await session.scalar(
            select(func.count(AuctionListing.id)).where(
                AuctionListing.is_active.is_(True)
            )
        )
        or 0
    )
    comparable_items = int(
        await session.scalar(
            select(func.count(distinct(AuctionListing.normalized_item_id))).where(
                AuctionListing.is_active.is_(True)
            )
        )
        or 0
    )
    freshness = freshness_for(
        latest_snapshot.fetched_at if latest_snapshot else None,
        stale_after_seconds=max(120, settings.auction_poll_seconds * 3),
        source=latest_snapshot.source if latest_snapshot else None,
    )
    return {
        "freshness": freshness,
        "active_listings": active_count,
        "comparable_items": comparable_items,
        "last_source_updated_ms": latest_snapshot.source_updated_ms if latest_snapshot else None,
    }
