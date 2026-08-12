from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import BazaarHistoryPoint, BazaarSnapshot


async def prune_local_history(
    session: AsyncSession, settings: Settings, *, now: datetime | None = None
) -> dict[str, int]:
    """Keep the file-backed development database bounded without touching production data."""

    if not settings.database_url.startswith("sqlite"):
        return {"history_deleted": 0, "snapshots_deleted": 0}
    current = now or datetime.now(UTC)
    history_cutoff = current - timedelta(days=settings.bazaar_history_retention_days)
    snapshot_cutoff = current - timedelta(days=settings.bazaar_snapshot_retention_days)
    history_result = await session.execute(
        delete(BazaarHistoryPoint).where(BazaarHistoryPoint.observed_at < history_cutoff)
    )
    snapshot_result = await session.execute(
        delete(BazaarSnapshot).where(BazaarSnapshot.fetched_at < snapshot_cutoff)
    )
    await session.commit()
    return {
        "history_deleted": history_result.rowcount or 0,
        "snapshots_deleted": snapshot_result.rowcount or 0,
    }
