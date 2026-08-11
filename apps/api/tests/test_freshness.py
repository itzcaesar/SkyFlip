from datetime import UTC, datetime, timedelta

from app.services.freshness import freshness_for


def test_freshness_exposes_unavailable_delayed_and_stale_states() -> None:
    now = datetime.now(UTC)
    assert freshness_for(None).status == "UNAVAILABLE"
    assert (
        freshness_for(now - timedelta(seconds=20), now=now, stale_after_seconds=120).status
        == "LIVE"
    )
    assert (
        freshness_for(now - timedelta(seconds=180), now=now, stale_after_seconds=120).status
        == "DELAYED"
    )
    assert (
        freshness_for(now - timedelta(seconds=700), now=now, stale_after_seconds=120).status
        == "STALE"
    )
