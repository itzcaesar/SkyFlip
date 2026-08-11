from datetime import UTC, datetime
from typing import Literal

from ..schemas import FreshnessResponse


def utc_now() -> datetime:
    return datetime.now(UTC)


def freshness_for(
    last_success_at: datetime | None,
    *,
    now: datetime | None = None,
    stale_after_seconds: int = 120,
    source: str | None = None,
) -> FreshnessResponse:
    """Return an explicit market-data state; no state is silently treated as live."""

    if last_success_at is None:
        return FreshnessResponse(
            status="UNAVAILABLE",
            source=None,
            message="No successful market update has been recorded.",
        )

    normalized_source: Literal["hypixel", "demo"] | None = None
    if source == "hypixel":
        normalized_source = "hypixel"
    elif source == "demo":
        normalized_source = "demo"

    current = now or utc_now()
    if last_success_at.tzinfo is None:
        last_success_at = last_success_at.replace(tzinfo=UTC)
    age = max(0, int((current - last_success_at).total_seconds()))
    status: Literal["LIVE", "DELAYED", "STALE", "UNAVAILABLE"]
    if age <= stale_after_seconds:
        status = "LIVE"
        message = f"Updated {age}s ago."
    elif age <= stale_after_seconds * 5:
        status = "DELAYED"
        message = f"Latest update is {age}s old."
    else:
        status = "STALE"
        message = f"Latest update is {age}s old; new data is required."
    return FreshnessResponse(
        status=status,
        source=normalized_source,
        last_success_at=last_success_at,
        age_seconds=age,
        message=message,
    )
