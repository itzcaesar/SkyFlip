# SkyFlip

SkyFlip is a real-data market intelligence terminal for Hypixel SkyBlock Bazaar and Auction House markets. The repository currently delivers the Phase 1 foundation and the first functional vertical slice:

`Hypixel Bazaar API → resilient worker → PostgreSQL → explainable analytics → FastAPI → Next.js screener`

The Auction House pipeline and informational Fabric companion are intentionally sequenced after this foundation. No part of SkyFlip automates purchases, menu clicks, order placement, claims, selling, or other Minecraft gameplay.

## Current status

- FastAPI backend with OpenAPI at `/docs`.
- PostgreSQL schema and Alembic migration for Bazaar snapshots, normalized metrics, history, and alert-event storage.
- Redis-backed worker lock, heartbeat, and SSE event channel.
- Hypixel Bazaar collector with timeout handling, retries, rate-limit handling, idempotent snapshot hashing, and stale-data propagation.
- Bazaar order→sell and instant→instant analytics, configurable fees, liquidity/fill estimates, history-aware volatility/momentum, anomaly gates, confidence, risk, and explainable 0–100 opportunity scoring.
- Local watchlists and throttled alerts, persisted market settings, capital allocation calculator, and history-based item valuation.
- Next.js terminal-style Dashboard, Bazaar screener, item detail/history, alerts, tools, and settings views.
- Core Python and frontend tests.

Auction House navigation is visible as a planned module but is disabled until its item normalization and comparable-sales dependencies are implemented. The UI never falls back to fake production prices.

## Requirements

- Node.js 20.9+ and pnpm 10+ for the web app.
- Python 3.11+ locally; the provided container uses Python 3.12.
- A Hypixel API key when the API account or endpoint requires one.
- Docker Desktop is optional for the current local-first workflow.

## Local setup

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\apps\api[dev]"

# Terminal 1 — API + local SQLite collector
cd apps/api
uvicorn app.main:app --reload --port 8000

# Terminal 2 — web
cd ..\web
pnpm install
pnpm dev
```

In local mode, the API creates `data/skyflip.db` automatically and runs the Bazaar collector in-process when `LOCAL_COLLECTOR_ENABLED=true`. Redis, Docker, a separate worker, and a manual migration are not required.

The first local API response may be `UNAVAILABLE` while the collector is making its first upstream request. Local mode uses the upstream Hypixel Bazaar feed by default and never substitutes fake prices. If you intentionally set `LOCAL_DEMO_ENABLED=true` in development, a failed live request may load a clearly labelled deterministic fixture, and the development-only `POST /api/bazaar/demo` endpoint can be used for UI testing.

The local settings screen persists fee, freshness, anomaly, and retention overrides in SQLite. Watchlists and alerts are single-profile local features until authentication is introduced. Raw history is automatically pruned, while hourly and daily chart candles remain available for longer windows.

For later PostgreSQL/Redis integration testing, use Docker after creating `.env`:

```powershell
cd C:\Projects\skyflip
docker compose up -d postgres redis
docker compose up --build api worker
cd apps/web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Real Bazaar data appears after the local collector successfully completes its first cycle. If Hypixel or a service is unavailable and demo mode is disabled, SkyFlip shows `UNAVAILABLE`, `DELAYED`, or `STALE`; it does not silently manufacture values.

## Tests and quality checks

```powershell
cd apps/api
pip install -e ".[dev]"
pytest
ruff check app tests

cd ..\web
pnpm test
pnpm lint
pnpm build
```

## Repository layout

```text
apps/
  api/          FastAPI app, SQLAlchemy models, migrations, analytics, tests
  worker/       Idempotent Bazaar polling worker with Redis lock/heartbeat
  web/          Next.js App Router terminal UI
packages/
  shared/       Reserved for cross-app contracts
  market-engine Reserved for the Auction House and shared engine extraction
  item-parser/  Reserved for type-specific AH normalization
  database/     Reserved for generated/shared database tooling
  api-client/   Reserved for generated clients
  ui/           Reserved for shared UI primitives
infrastructure/ Docker build files
docs/           Architecture and market-engine decisions
```

## API quick reference

- `GET /api/health`
- `GET /api/bazaar/status`
- `POST /api/bazaar/refresh` (development-only immediate upstream fetch)
- `POST /api/bazaar/demo` (development-only explicit local demo dataset)
- `GET /api/bazaar/products`
- `GET /api/bazaar/opportunities`
- `GET /api/bazaar/products/{productId}`
- `GET /api/bazaar/products/{productId}/history`
- `POST /api/bazaar/capital-optimize`
- `GET /api/items/search?q=...`
- `GET/PATCH/DELETE /api/settings`
- `GET/POST/DELETE /api/watchlist`
- `GET /api/alerts`, `POST /api/alerts/{id}/read`, `POST /api/alerts/read-all`
- `GET /api/valuator?product_id=...`
- `GET /api/events` (SSE)

## Data policy

Source payloads are identified by a canonical SHA-256 hash. Identical upstream snapshots do not create duplicate historical rows. New live observations are retained as raw points for short-term analysis and merged into durable hourly and daily OHLC-style chart candles. The default local policy keeps raw points for 7 days, chart candles for 90 days, and source snapshots for 30 days.

The configured Bazaar fee policy is centralized in `apps/api/app/config.py` and `apps/api/app/services/bazaar_engine.py`. It includes platform buy/sell fees plus a separate execution buffer for quote movement between observation and fill. Change it through environment variables or the local settings screen and document the policy before changing production interpretation.

`apps/api/tests/fixtures/bazaar_response.json` is a clearly labeled development/test fixture. It is not imported by the production worker and cannot silently become a production fallback.

## Roadmap

1. Add Auction House ingestion, NBT/item normalization, fingerprints, comparable matching, valuation, anomaly detection, and mispricing screens.
2. Add authentication and multi-profile watchlists after the local single-profile workflow is stable.
3. Add the informational Fabric companion after the web/backend core is stable.
4. Move from local SQLite to PostgreSQL/Redis worker deployment with production monitoring.
