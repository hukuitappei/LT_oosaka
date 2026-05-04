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
- Learning item search, filtering, status tracking, and reuse recording

## Architecture

- `web/`: Next.js app for end users
- `api/`: FastAPI backend
- `worker`: Celery worker using the same `api/` image
- `scheduler`: Celery Beat scheduler for periodic jobs
- `db`: PostgreSQL in Docker Compose, SQLite for lighter local work
- `cache`: Redis for Celery
- `llm`: Ollama for local model access

The frontend talks to the backend through `API_URL`. In local development it defaults to `http://localhost:8000`. In the browser it proxies through `/api/backend`.

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

## API Highlights

- `GET /learning-items/`
  - Supports `q`, `repository_id`, `pr_id`, `category`, `status`, `visibility`, `limit`, and `offset`
- `GET /learning-items/summary`
  - Returns learning and reuse summary metrics
- `PATCH /learning-items/{item_id}`
  - Updates `status` and/or `visibility`
- `GET /pull-requests/{id}`
  - Returns PR details plus related learning recommendations
- `POST /pull-requests/{id}/related-learning/{item_id}/reuse`
  - Records related learning reuse
- `GET /github-connections/`
  - Lists visible GitHub connections for the current workspace/user context

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

Current local verification as of 2026-05-04:

- `api`: run after merge resolution
- `web`: run after merge resolution

## Notes

- The data retention and minimization policy lives in [docs/data-handling-policy.md](docs/data-handling-policy.md).
- The staging verification checklist lives in [docs/staging-verification-checklist.md](docs/staging-verification-checklist.md).
- Webhook, Celery, and digest logs include stable tracing fields such as `event_type`, `action`, `workspace_id`, `pr_number`, `installation_id`, `pr_id`, `year`, and `week`.
- Docker Compose verification was not run in the current environment unless explicitly stated.
