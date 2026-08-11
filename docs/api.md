# API contract

FastAPI publishes the generated OpenAPI document at `/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`.

## Bazaar screener

`GET /api/bazaar/products`

Useful query parameters include `search`, `min_profit`, `min_roi`, `max_capital`, `min_volume`, `min_liquidity`, `max_fill_time`, `risk_level`, `min_score`, `min_confidence`, `flip_type`, `page`, `page_size`, `sort_by`, `sort_dir`, and `include_stale`.

The response includes `items`, pagination, and a `freshness` object. Numeric fields are serialized as numbers; timestamps are ISO 8601.

`POST /api/bazaar/refresh` performs one immediate upstream fetch in non-production local mode. Production ingestion remains worker-owned.

## Capital optimizer

`POST /api/bazaar/capital-optimize`

The request accepts available capital, risk preference, maximum fill time, minimum ROI/liquidity, and concurrent flip count. The response labels projected profit as an estimate and includes reserve capital. It never claims that a projection is guaranteed.

## Live events

`GET /api/events` is Server-Sent Events. Current event types include `bazaar.updated` and `market.warning`. The web app reconnects through the browser EventSource implementation and invalidates its query cache when a Bazaar update arrives.
