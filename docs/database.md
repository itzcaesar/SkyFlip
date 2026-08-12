# Database design

The first migration is `apps/api/migrations/versions/0001_initial.py`.

## Bazaar tables

- `bazaar_products`: stable product identity, display label, active state, and last successful source metadata.
- `bazaar_snapshots`: one row per unique canonical upstream payload hash. The full response is not duplicated.
- `bazaar_opportunities`: one current row per product and flip type. This is the screener read model and includes the score breakdown, explanations, freshness, liquidity, risk, and confidence.
- `bazaar_history`: normalized observation points used for product charts and future volatility/momentum aggregation.
- `watchlist_items`: local single-profile item/strategy thresholds.
- `alert_events`: throttled internal watchlist signal events; no external notification is implied.
- `app_settings`: local market-policy overrides; secrets are never stored here.

## Index choices

- Current opportunity score, observation time, and filter fields are indexed for screener queries.
- Product history is indexed by product, flip type, and observation time.
- Snapshot fetch time and alert creation time support retention jobs.

## Retention policy

Local mode now prunes normalized points and snapshots using configurable retention windows. Before production scale-up:

1. Keep high-frequency source observations for a short configurable window.
2. Aggregate 1m/5m/15m/1h/4h/1d candles with open/high/low/close/median/volume/sample count.
3. Keep critical auction sale records and daily aggregates longer.
4. Delete or compact redundant raw/source records after validation.

No retention job deletes data yet; it must be implemented with explicit metrics and a dry-run before enabling deletion.
