# SkyFlip

SkyFlip is a real-data market intelligence terminal for Hypixel SkyBlock Bazaar and Auction House markets. The repository currently delivers the Phase 1 foundation and the first functional vertical slice:

`Hypixel Bazaar API → resilient worker → PostgreSQL → explainable analytics → FastAPI → Next.js screener`

The Auction House pipeline and informational Fabric companion are intentionally sequenced after this foundation. No part of SkyFlip automates purchases, menu clicks, order placement, claims, selling, or other Minecraft gameplay.

## Current status

- FastAPI backend with OpenAPI at `/docs`.
- PostgreSQL schema and Alembic migration for Bazaar snapshots, normalized metrics, history, and alert-event storage.
- Redis-backed worker lock, heartbeat, and SSE event channel.
- Hypixel Bazaar collector with timeout handling, retries, rate-limit handling, idempotent snapshot hashing, and stale-data propagation.
- Bazaar order→sell and instant→instant analytics, configurable fees, liquidity/fill estimates, confidence, risk, and explainable 0–100 opportunity scoring.
- Next.js terminal-style Dashboard, Bazaar screener, and Bazaar item detail/history views.
- Core Python and frontend tests.

Auction House navigation is visible as a planned module but is disabled until its item normalization and comparable-sales dependencies are implemented. The UI never falls back to fake production prices.

## Requirements

- Docker Desktop with Compose.
- Node.js 20.9+ and pnpm 10+ for the web app.
- Python 3.11+ locally; the provided container uses Python 3.12.
- A Hypixel API key when the API account or endpoint requires one.

## Local setup

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis

cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head

# Terminal 1 — API
uvicorn app.main:app --reload --port 8000

# Terminal 2 — worker, from apps/api with the venv active
$env:PYTHONPATH = (Get-Location).Path
python ..\worker\worker.py

# Terminal 3 — web
cd ..\web
pnpm install
pnpm dev
```

Or use Docker for the backend services after creating `.env`:

```powershell
docker compose up --build api worker
cd apps/web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Real Bazaar data appears after the worker successfully completes its first cycle. If Hypixel or a service is unavailable, SkyFlip shows `UNAVAILABLE`, `DELAYED`, or `STALE`; it does not manufacture values.

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
- `GET /api/bazaar/products`
- `GET /api/bazaar/opportunities`
- `GET /api/bazaar/products/{productId}`
- `GET /api/bazaar/products/{productId}/history`
- `POST /api/bazaar/capital-optimize`
- `GET /api/items/search?q=...`
- `GET /api/events` (SSE)

## Data policy

Source payloads are identified by a canonical SHA-256 hash. Identical upstream snapshots do not create duplicate historical rows. Normalized metric history is retained for charting; a later retention job will aggregate high-frequency observations into longer-lived candles before raw retention is expanded.

The configured Bazaar fee policy is centralized in `apps/api/app/config.py` and `apps/api/app/services/bazaar_engine.py`. Change it through environment variables and document the policy before changing production interpretation.

`apps/api/tests/fixtures/bazaar_response.json` is a clearly labeled development/test fixture. It is not imported by the production worker and cannot silently become a production fallback.

## Roadmap

1. Expand Bazaar aggregation, alert events, watchlists, settings, and capital allocation UX.
2. Add Auction House ingestion, NBT/item normalization, fingerprints, comparable matching, valuation, anomaly detection, and mispricing screens.
3. Add the informational Fabric companion after the web/backend core is stable.
