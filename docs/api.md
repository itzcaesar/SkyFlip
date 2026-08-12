# API contract

FastAPI publishes the generated OpenAPI document at `/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`.

## Bazaar screener

`GET /api/bazaar/products`

Useful query parameters include `search`, `min_profit`, `min_roi`, `max_capital`, `min_volume`, `min_liquidity`, `max_fill_time`, `risk_level`, `min_score`, `min_confidence`, `flip_type`, `page`, `page_size`, `sort_by`, `sort_dir`, and `include_stale`.

The response includes `items`, pagination, and a `freshness` object. Numeric fields are serialized as numbers; timestamps are ISO 8601.

Only current, non-stale, qualified opportunities are returned by default. Extreme ROI and quote-ratio anomalies remain available on item detail but are excluded from qualified screens.

`POST /api/bazaar/refresh` performs one immediate upstream fetch in non-production local mode. Production ingestion remains worker-owned.

`POST /api/bazaar/demo` loads the deterministic local dataset only when `LOCAL_DEMO_ENABLED=true` and `APP_ENV` is not production. Responses expose `freshness.source=demo`, and the web app displays a `DEMO DATA` badge. Demo values are never a live-market fallback in production.

`GET /api/bazaar/products/{productId}/history?range=7d&resolution=auto` supports `range=6h|24h|7d|30d|90d` and `resolution=auto|raw|hour|day`. `auto` uses raw observations for short ranges, hourly candles for 7 days, and daily candles for longer windows. Points include buy/sell OHLC values, spread, volume, liquidity, opportunity score, and `sample_count`; the response also includes a range summary.

## Capital optimizer

`POST /api/bazaar/capital-optimize`

The request accepts available capital, risk preference, maximum fill time, minimum ROI/liquidity, and concurrent flip count. The response labels projected profit as an estimate and includes reserve capital. It never claims that a projection is guaranteed.

## Local tools

- `GET/PATCH/DELETE /api/settings` reads, updates, or resets the local market policy stored in SQLite.
- `GET/POST/DELETE /api/watchlist` manages the single local watchlist profile.
- `GET /api/alerts` returns throttled watchlist signal events. `POST /api/alerts/{id}/read` and `POST /api/alerts/read-all` acknowledge them.
- `GET /api/valuator?product_id=...` summarizes current quotes, retained price range, change, volatility, liquidity, and confidence.

## Live events

`GET /api/events` is Server-Sent Events. Current event types include `bazaar.updated` and `market.warning`. The web app reconnects through the browser EventSource implementation and invalidates its query cache when a Bazaar update arrives.
