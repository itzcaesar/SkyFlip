# Deployment notes

SkyFlip keeps web, API, worker, PostgreSQL, and Redis provider-agnostic.

- Web: Node.js server or container; Vercel is compatible with the Next.js app.
- API: container or Python process on Railway, Render, VPS, or equivalent.
- Worker: separate long-running container/process with the same environment and database/Redis access.
- PostgreSQL and Redis: managed services are recommended for production.

Set `APP_ENV=production`, a strong `APP_SECRET`, explicit `CORS_ORIGINS`, and server-side `HYPIXEL_API_KEY`. Do not expose the key with a `NEXT_PUBLIC_` variable. Run `alembic upgrade head` as a release step before starting the API.

Production monitoring should alert on worker heartbeat age, collection failures, stale Bazaar age, database errors, Redis errors, and the ratio of invalid upstream product records. The service must remain honest about unavailable data during an outage.

