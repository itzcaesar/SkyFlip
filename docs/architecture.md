# SkyFlip architecture

## Phase 1 data flow

```text
Hypixel Bazaar endpoint
        │ retries / timeout / rate awareness
        ▼
worker.collect_bazaar
        │ canonical payload hash + normalization
        ├── PostgreSQL: products, snapshots, current opportunities, history
        ├── Redis: worker heartbeat + distributed collector lock
        └── Redis Pub/Sub: bazaar.updated
                              │
                              ▼
                        FastAPI SSE /api/events
                              │
                              ▼
                         Next.js Query cache
```

The API is read-oriented for market data. The worker owns upstream collection and is the only component that writes new market observations. This avoids request-driven polling storms and makes stale data explicit.

## Service boundaries

- `apps/api/app/services/hypixel_client.py`: upstream HTTP concerns only.
- `apps/api/app/services/collector.py`: idempotent persistence and event publication.
- `apps/api/app/services/bazaar_engine.py`: pure Bazaar calculations.
- `apps/api/app/services/scoring.py`: the single explainable opportunity scoring policy.
- `apps/api/app/services/freshness.py`: live/delayed/stale/unavailable policy.
- `apps/worker/worker.py`: scheduling, distributed lock, heartbeat, and failure logging.
- `apps/web`: presentation and query invalidation; it never receives the Hypixel secret.

## Failure behavior

An upstream failure marks existing Bazaar opportunity rows stale and leaves their last known values untouched. API responses expose freshness. The web application renders a useful unavailable/error state rather than a synthetic result. Event streaming is best-effort and cannot roll back a successful market commit.

## Extension points

Auction House ingestion should use the same worker boundary but separate jobs for raw auction capture, NBT decoding, normalization, comparable grouping, valuation, anomaly analysis, and opportunity publication. The current `packages/item-parser` and `packages/market-engine` directories are reserved for extracting those shared primitives without coupling them to web routes.

