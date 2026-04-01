# PR Knowledge Hub

PR Knowledge Hub is a monorepo for turning pull request review feedback into reusable learning items and weekly digests.

The active application is the `api/` FastAPI backend plus the `web/` Next.js frontend.

## Current Scope

- Email/password auth with personal workspaces
- Workspace-scoped repositories, pull requests, learning items, and weekly digests
- GitHub App / token connection records
- Webhook-driven PR ingestion
- LLM-based learning extraction
- Celery-based async extraction, digest generation, and PR reanalysis
- Dashboard, learning items, and weekly digest pages
- Learning item search, filtering, and status tracking (`new`, `in_progress`, `applied`, `ignored`)

## Architecture

- `web/`: Next.js app for end users
- `api/`: FastAPI backend
- `worker`: Celery worker using the same `api/` image
- `scheduler`: Celery Beat scheduler for periodic jobs
- `db`: PostgreSQL in Docker Compose, SQLite for lighter local work
- `cache`: Redis for Celery
- `llm`: Ollama for local model access

The frontend talks to the backend through `API_URL`. In local development it defaults to `http://localhost:8000`. In Docker Compose it is set to `http://api:8000`.

## Quick Start

### Docker Compose

1. Copy `.env.example` to `.env`.
2. Fill in the required secrets.
3. Start the stack:

```bash
docker compose up --build
```

4. Open:
- Web: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

The API container runs `alembic upgrade head` on startup.

### Local Development

Backend:

```bash
cd api
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt -r requirements-test.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`app.main:app` is the production-style entrypoint. It does not mount the fixture-backed `/analyze` routes.
Use the fixture samples under `api/fixtures/` from tests or ad hoc local checks when you need to inspect extraction behavior.

Frontend:

```bash
cd web
npm install
npm run dev
```

Worker:

```bash
cd api
celery -A app.celery_app worker --loglevel=info
```

Scheduler:

```bash
cd api
celery -A app.celery_app beat --loglevel=info
```

Demo data:

```bash
cd api
python scripts/seed_demo_data.py
```

This creates a loginable demo account:

- Email: `demo@example.com`
- Password: `demo12345`

## Learning Item Workflow

### API

- `GET /learning-items/`
  - Supports `q`, `repository_id`, `pr_id`, `category`, `status`, `visibility`, `limit`, and `offset`
- `GET /learning-items/summary`
  - Returns `total_learning_items`, `current_week_count`, `weekly_points`, `top_categories`, and `status_counts`
- `PATCH /learning-items/{item_id}`
  - Updates `status` and/or `visibility`

### Statuses

- `new`
- `in_progress`
- `applied`
- `ignored`

## Testing

Backend:

```bash
cd api
pytest -q
```

Frontend:

```bash
cd web
npm run lint
npm run build
npm run test:e2e
```

Current local verification as of 2026-04-01:

- `api`: `94 passed`
- `web`: `npm run lint` passes
- `web`: `npm run build` passes
- `web`: `npm run test:e2e` passes

## CI

GitHub Actions runs:

- `api`: `pytest -q`
- `web`: `npm ci && npm run lint && npm run build`
- `web-e2e`: `npm ci && npx playwright install --with-deps chromium && npm run test:e2e`

Workflow file:

- `.github/workflows/ci.yml`

## Main User Flow

1. Register or log in at `/login`.
2. Use the default personal workspace.
3. Connect GitHub through the backend integration endpoints.
4. Receive webhook-driven PR ingestion and extraction.
5. Review learning items on `/learning-items`.
6. Filter or search learning items and update their status.
7. Generate and read workspace-scoped digests on `/weekly-digests`.
8. Reanalyze an existing PR through the API, executed asynchronously by Celery.

## GitHub App Setup

The webhook ingestion path in this repository is:

- Webhook URL: `https://<your-api-host>/webhooks/github`

Example local tunnel URL:

- `https://<your-ngrok-subdomain>.ngrok.app/webhooks/github`

### Required Environment Variables

Set these in `.env` for GitHub App based webhook ingestion:

```env
GITHUB_APP_ID=<github_app_id>
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=<random_webhook_secret>
```

### GitHub App Settings

Repository permissions:

- `Metadata`: `Read-only`
- `Pull requests`: `Read-only`

Subscribe to these webhook events:

- `Pull request`
- `Pull request review`
- `Pull request review comment`

### Runtime Services

For webhook processing to work, these services must be running:

- `api`
- `worker`

The `scheduler` service is not required for webhook ingestion itself.
It is only used for periodic jobs such as weekly digest generation.

## Development Notes

- The fixture-backed `/analyze` router is intentionally excluded from `app.main:app`.
- `api/fixtures/` is a development and test aid for extraction behavior, not a production API surface.
- `workspace` is the primary ownership boundary.
- Heavy background work uses Celery instead of FastAPI `BackgroundTasks`.
- Webhook, Celery, and digest logs include stable tracing fields such as `event_type`, `action`, `workspace_id`, `pr_number`, `installation_id`, `pr_id`, `year`, and `week`.

## Required Environment Variables

Defined in `.env.example`:

- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `OLLAMA_BASE_URL`
- `SECRET_KEY`
- `APP_ENV`
- `WEEKLY_DIGEST_SCHEDULE_MINUTE`
- `WEEKLY_DIGEST_SCHEDULE_HOUR`
- `WEEKLY_DIGEST_SCHEDULE_DAY_OF_WEEK`
- `CORS_ORIGINS`
- `GITHUB_APP_ID`
- `GITHUB_PRIVATE_KEY`
- `GITHUB_WEBHOOK_SECRET`
- `GITHUB_OAUTH_CLIENT_ID`
- `GITHUB_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI`

## Current Limitations

- GitHub integrations are not usable without the corresponding app or OAuth secrets.
- LLM-based extraction depends on either Anthropic or Ollama being configured.
- Docker Compose verification was not run in the current environment because Docker was unavailable there.
