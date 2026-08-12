# Database design

The initial schema is `apps/api/migrations/versions/0001_initial.py`; local tools are in `0002_local_tools.py` and durable history candles are in `0003_history_rollups.py`.

## Bazaar tables

- `bazaar_products`: stable product identity, display label, active state, and last successful source metadata.
- `bazaar_snapshots`: one row per unique canonical upstream payload hash. The full response is not duplicated.
- `bazaar_opportunities`: one current row per product and flip type. This is the screener read model and includes the score breakdown, explanations, freshness, liquidity, risk, and confidence.
- `bazaar_history`: high-frequency normalized observation points used for short-term charts and history-aware scoring.
- `bazaar_history_rollups`: durable hourly and daily candles with buy/sell open, high, low, close, volume, liquidity, score, and sample count.
- `watchlist_items`: local single-profile item/strategy thresholds.
- `alert_events`: throttled internal watchlist signal events; no external notification is implied.
- `app_settings`: local market-policy overrides; secrets are never stored here.

## Index choices

- Current opportunity score, observation time, and filter fields are indexed for screener queries.
- Product history is indexed by product, flip type, and observation time.
- Snapshot fetch time, rollup interval/bucket, and alert creation time support bounded local maintenance.

## Retention policy

Local mode prunes raw points, hourly candles, daily candles, and snapshots using configurable retention windows. The default policy is short raw history plus a longer chart trail. Before production scale-up:

1. Keep high-frequency source observations for a short configurable window.
2. Add finer-grained 1m/5m/15m/4h candles only if the live polling interval and chart UX justify them.
3. Keep critical auction sale records and daily aggregates longer.
4. Delete or compact redundant raw/source records after validation.

The local collector performs rollup maintenance after a new upstream snapshot. Existing databases are backfilled once from retained raw points when the new rollup table is first used.
