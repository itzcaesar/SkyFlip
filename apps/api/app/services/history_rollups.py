"""Build durable chart candles from high-frequency Bazaar observations."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BazaarHistoryPoint, BazaarHistoryRollup

INTERVALS = ("hour", "day")


@dataclass(frozen=True)
class HistoryObservation:
    product_id: str
    flip_type: str
    observed_at: datetime
    buy_price: float
    sell_price: float
    volume: int
    liquidity: float
    opportunity_score: float
    source_updated_ms: int


@dataclass
class _Bucket:
    product_id: str
    flip_type: str
    interval: str
    bucket_start: datetime
    first_at: datetime
    buy_open: float
    buy_high: float
    buy_low: float
    buy_close: float
    sell_open: float
    sell_high: float
    sell_low: float
    sell_close: float
    volume: int
    liquidity_total: float
    opportunity_score_total: float
    sample_count: int
    source_updated_ms: int

    @classmethod
    def from_observation(
        cls, observation: HistoryObservation, interval: str, bucket_start: datetime
    ) -> "_Bucket":
        return cls(
            product_id=observation.product_id,
            flip_type=observation.flip_type,
            interval=interval,
            bucket_start=bucket_start,
            first_at=observation.observed_at,
            buy_open=observation.buy_price,
            buy_high=observation.buy_price,
            buy_low=observation.buy_price,
            buy_close=observation.buy_price,
            sell_open=observation.sell_price,
            sell_high=observation.sell_price,
            sell_low=observation.sell_price,
            sell_close=observation.sell_price,
            volume=max(0, observation.volume),
            liquidity_total=observation.liquidity,
            opportunity_score_total=observation.opportunity_score,
            sample_count=1,
            source_updated_ms=observation.source_updated_ms,
        )

    def add(self, observation: HistoryObservation) -> None:
        if observation.observed_at < self.first_at:
            self.first_at = observation.observed_at
            self.buy_open = observation.buy_price
            self.sell_open = observation.sell_price
        self.buy_high = max(self.buy_high, observation.buy_price)
        self.buy_low = min(self.buy_low, observation.buy_price)
        self.buy_close = observation.buy_price
        self.sell_high = max(self.sell_high, observation.sell_price)
        self.sell_low = min(self.sell_low, observation.sell_price)
        self.sell_close = observation.sell_price
        self.volume += max(0, observation.volume)
        self.liquidity_total += observation.liquidity
        self.opportunity_score_total += observation.opportunity_score
        self.sample_count += 1
        self.source_updated_ms = max(self.source_updated_ms, observation.source_updated_ms)

    @property
    def liquidity(self) -> float:
        return self.liquidity_total / max(self.sample_count, 1)

    @property
    def opportunity_score(self) -> float:
        return self.opportunity_score_total / max(self.sample_count, 1)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def bucket_start(observed_at: datetime, interval: str) -> datetime:
    current = _utc(observed_at)
    if interval == "hour":
        return current.replace(minute=0, second=0, microsecond=0)
    if interval == "day":
        return current.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unsupported history rollup interval: {interval}")


def _aggregate(
    observations: list[HistoryObservation],
) -> dict[tuple[str, str, str, datetime], _Bucket]:
    buckets: dict[tuple[str, str, str, datetime], _Bucket] = {}
    for observation in observations:
        for interval in INTERVALS:
            start = bucket_start(observation.observed_at, interval)
            key = (observation.product_id, observation.flip_type, interval, start)
            current = buckets.get(key)
            if current is None:
                buckets[key] = _Bucket.from_observation(observation, interval, start)
            else:
                current.add(observation)
    return buckets


async def upsert_history_rollups(
    session: AsyncSession, observations: list[HistoryObservation]
) -> int:
    """Merge new observations into hourly and daily candles.

    The collector only passes observations from a new upstream snapshot, so this operation
    is idempotent with the collector's payload-hash guard and does not double-count retries.
    """

    buckets = _aggregate(observations)
    if not buckets:
        return 0

    bucket_starts = {key[3] for key in buckets}
    existing_rows = (
        await session.scalars(
            select(BazaarHistoryRollup).where(
                BazaarHistoryRollup.interval.in_(INTERVALS),
                BazaarHistoryRollup.bucket_start.in_(bucket_starts),
            )
        )
    ).all()
    existing = {
        (row.product_id, row.flip_type, row.interval, _utc(row.bucket_start)): row
        for row in existing_rows
    }
    for key, aggregate in buckets.items():
        row = existing.get(key)
        if row is None:
            row = BazaarHistoryRollup(
                product_id=aggregate.product_id,
                flip_type=aggregate.flip_type,
                interval=aggregate.interval,
                bucket_start=aggregate.bucket_start,
                buy_open=aggregate.buy_open,
                buy_high=aggregate.buy_high,
                buy_low=aggregate.buy_low,
                buy_close=aggregate.buy_close,
                sell_open=aggregate.sell_open,
                sell_high=aggregate.sell_high,
                sell_low=aggregate.sell_low,
                sell_close=aggregate.sell_close,
                volume=aggregate.volume,
                liquidity=aggregate.liquidity,
                opportunity_score=aggregate.opportunity_score,
                sample_count=aggregate.sample_count,
                source_updated_ms=aggregate.source_updated_ms,
            )
            session.add(row)
            continue

        old_count = max(row.sample_count, 0)
        new_count = old_count + aggregate.sample_count
        row.buy_high = Decimal(str(max(float(row.buy_high), aggregate.buy_high)))
        row.buy_low = Decimal(str(min(float(row.buy_low), aggregate.buy_low)))
        row.buy_close = Decimal(str(aggregate.buy_close))
        row.sell_high = Decimal(str(max(float(row.sell_high), aggregate.sell_high)))
        row.sell_low = Decimal(str(min(float(row.sell_low), aggregate.sell_low)))
        row.sell_close = Decimal(str(aggregate.sell_close))
        row.volume = int(row.volume) + aggregate.volume
        row.liquidity = Decimal(
            str(
                (
                    float(row.liquidity) * old_count
                    + aggregate.liquidity * aggregate.sample_count
                )
                / max(new_count, 1)
            )
        )
        row.opportunity_score = Decimal(
            str(
                (
                    float(row.opportunity_score) * old_count
                    + aggregate.opportunity_score * aggregate.sample_count
                )
                / max(new_count, 1)
            )
        )
        row.sample_count = new_count
        row.source_updated_ms = max(row.source_updated_ms, aggregate.source_updated_ms)

    await session.commit()
    return len(buckets)


async def ensure_history_rollups(session: AsyncSession) -> int:
    """Backfill rollups once for a database created before the rollup feature."""

    has_rollups = await session.scalar(select(BazaarHistoryRollup.id).limit(1))
    if has_rollups is not None:
        return 0
    rows = (
        await session.scalars(
            select(BazaarHistoryPoint).order_by(
                BazaarHistoryPoint.product_id,
                BazaarHistoryPoint.flip_type,
                BazaarHistoryPoint.observed_at,
            )
        )
    ).all()
    observations = [
        HistoryObservation(
            product_id=row.product_id,
            flip_type=row.flip_type,
            observed_at=row.observed_at,
            buy_price=float(row.buy_price),
            sell_price=float(row.sell_price),
            volume=row.volume,
            liquidity=float(row.liquidity),
            opportunity_score=float(row.opportunity_score),
            source_updated_ms=row.source_updated_ms,
        )
        for row in rows
    ]
    return await upsert_history_rollups(session, observations)


def observation_from_result(
    *,
    product_id: str,
    flip_type: str,
    observed_at: datetime,
    result: Any,
    source_updated_ms: int,
) -> HistoryObservation:
    return HistoryObservation(
        product_id=product_id,
        flip_type=flip_type,
        observed_at=observed_at,
        buy_price=float(result.buy_price),
        sell_price=float(result.sell_price),
        volume=int(result.transaction_volume),
        liquidity=float(result.estimated_liquidity),
        opportunity_score=float(result.opportunity_score),
        source_updated_ms=source_updated_ms,
    )
