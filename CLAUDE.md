# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PR Knowledge Hub — a monorepo that turns GitHub PR review feedback into reusable learning items and weekly digests.

- `api/` — FastAPI backend (Python, async SQLAlchemy, Celery)
- `web/` — Next.js 15 frontend (TypeScript, Tailwind CSS, Playwright E2E)
- `migrations/` — Alembic migrations

## Commands

### Backend

```bash
cd api
pytest -q                                      # all 137 tests
pytest -q tests/test_auth.py                   # single file
pytest -q tests/test_auth.py::test_register    # single test

uvicorn app.main:app --reload --port 8000      # dev server
alembic -c migrations/alembic.ini upgrade head # apply migrations
python scripts/seed_demo_data.py               # seed demo@example.com / demo12345

celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

### Frontend

```bash
cd web
npm run dev               # port 3000
npm run lint
npm run build
npm run test:e2e          # full E2E (spawns mock API + Next.js at port 3100)
npm run test:e2e:headed   # same, with visible browser
```

### Full stack

```bash
docker compose up --build  # web :3000, api :8000, PostgreSQL, Redis, Ollama
```

## Architecture

### Auth & Workspace Scoping

Every request is scoped to a workspace. FastAPI dependency injection enforces this:
- `get_current_user()` validates the JWT token
- `get_current_workspace()` reads the `X-Workspace-Id` header (or `workspace_id` cookie)
- All service functions receive `workspace_id` and filter queries by it
- `require_workspace_role(allowed_roles)` gates role-sensitive endpoints

### Service Layer Pattern

Routers must not contain DB queries or business logic — those belong in `api/app/services/`. Routers call service functions and map exceptions to HTTP responses. Custom exceptions are raised in services and caught in routers.

### Celery Pipeline (4 Queues)

```
GitHub webhook → extract_pr_task        [webhook_ingest]
                → extract_learning_items_task  [learning_extract]
                
User trigger    → reanalyze_pr_task     [learning_extract]
Beat scheduler  → generate_scheduled_weekly_digests_task  [digest_generate]
                → cleanup_retention_task  [retention_cleanup]
```

All tasks have `max_retries=3`, structured log fields (`correlation_id`, `attempt`, `final`), and a `task_failure` signal handler in `celery_app.py` that logs permanently failed tasks at `ERROR` level. Retryable failures log at `WARNING`.

### LLM Abstraction

`BaseLLMProvider` in `api/app/llm/` supports Anthropic and Ollama interchangeably. `get_default_llm_provider()` selects based on config. Tests use `mock_llm_provider` (AsyncMock).

### Frontend API Proxy

Client-side `fetch` calls go to `/api/backend/<path>`, which Next.js proxies to the backend at `API_URL`. Server-side RSC calls use `API_URL` directly. This means `getApiBaseUrl()` returns `/api/backend` in the browser and `process.env.API_URL` on the server.

### E2E Test Infrastructure

`web/e2e/mock-api-server.mjs` is a lightweight Node HTTP server (port 4100) that stubs all backend routes. Token `e2e-token` returns fixture data; `e2e-empty` returns empty lists. `run-playwright.mjs` orchestrates startup: kills stale ports → starts mock API → starts Next.js (port 3100) → waits for health → runs Playwright. Click interactions on client components require `page.waitForLoadState("networkidle")` before clicking to avoid pre-hydration default form submission.

### Database

SQLite (`aiosqlite`) for local dev and tests; PostgreSQL (`asyncpg`) for Docker/production. Tests use an in-memory SQLite `AsyncSession` from the `db_session` fixture in `api/conftest.py`.

## Adding a New Endpoint

1. Create service function in `api/app/services/`
2. Create or extend router in `api/app/routers/`, injecting `get_current_workspace`
3. Register router in `api/app/factory.py`
4. Add tests in `api/tests/`

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing |
| `DATABASE_URL` | SQLite (`sqlite+aiosqlite:///./app.db`) or PostgreSQL |
| `REDIS_URL` | Celery broker/backend |
| `GITHUB_CONNECTION_TOKEN_ENCRYPTION_KEY` | Token encryption at rest |
| `ANTHROPIC_API_KEY` | LLM provider (or use Ollama) |
| `GITHUB_WEBHOOK_SECRET` | Required in staging/production |
