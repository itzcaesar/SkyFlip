from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import BazaarHistoryPoint, BazaarHistoryRollup, BazaarSnapshot


async def prune_local_history(
    session: AsyncSession, settings: Settings, *, now: datetime | None = None
) -> dict[str, int]:
    """Keep the file-backed development database bounded without touching production data."""

    if not settings.database_url.startswith("sqlite"):
        return {"history_deleted": 0, "rollups_deleted": 0, "snapshots_deleted": 0}
    current = now or datetime.now(UTC)
    history_cutoff = current - timedelta(days=settings.bazaar_history_retention_days)
    hourly_rollup_cutoff = history_cutoff
    daily_rollup_cutoff = current - timedelta(days=settings.bazaar_chart_retention_days)
    snapshot_cutoff = current - timedelta(days=settings.bazaar_snapshot_retention_days)
    history_result = await session.execute(
        delete(BazaarHistoryPoint).where(BazaarHistoryPoint.observed_at < history_cutoff)
    )
    hourly_rollup_result = await session.execute(
        delete(BazaarHistoryRollup).where(
            BazaarHistoryRollup.interval == "hour",
            BazaarHistoryRollup.bucket_start < hourly_rollup_cutoff,
        )
    )
    daily_rollup_result = await session.execute(
        delete(BazaarHistoryRollup).where(
            BazaarHistoryRollup.interval == "day",
            BazaarHistoryRollup.bucket_start < daily_rollup_cutoff,
        )
    )
    snapshot_result = await session.execute(
        delete(BazaarSnapshot).where(BazaarSnapshot.fetched_at < snapshot_cutoff)
    )
    await session.commit()
    history_deleted = int(getattr(history_result, "rowcount", 0) or 0)
    rollups_deleted = int(getattr(hourly_rollup_result, "rowcount", 0) or 0) + int(
        getattr(daily_rollup_result, "rowcount", 0) or 0
    )
    snapshots_deleted = int(getattr(snapshot_result, "rowcount", 0) or 0)
    return {
        "history_deleted": history_deleted,
        "rollups_deleted": rollups_deleted,
        "snapshots_deleted": snapshots_deleted,
    }
