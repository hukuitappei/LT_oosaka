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

## Architecture

- `web/`: Next.js app for end users
- `api/`: FastAPI backend
- `worker`: Celery worker using the same `api/` image
- `db`: PostgreSQL in Docker Compose, SQLite for lighter local work
- `cache`: Redis for Celery
- `llm`: Ollama for local model access

The frontend talks to the backend through `API_URL`. In local development it defaults to `http://localhost:8000`. In Docker Compose it is set to `http://api:8000`.

## Core Design Principle

PR Knowledge Hub is a `review knowledge extraction pipeline`.

The pipeline is intentionally staged:

- `Ingest`: receive external GitHub events and reduce them to stable task inputs
- `Scope Resolution`: resolve workspace ownership and repository boundaries before heavier work begins
- `Knowledge Extraction`: convert review comments into reusable learning items
- `Reflection`: aggregate workspace learnings into weekly digests
- `Lifecycle Control`: manage retention, cleanup, and purge windows explicitly

This keeps the HTTP layer thin, the service layer orchestration-focused, and the worker layer responsible for retryable background work.

## Pipeline Overview

- `Ingest`: GitHub webhooks are normalized, tagged with correlation metadata, and handed off to Celery
- `Scope Resolution`: the backend resolves the active workspace and repository mapping from the incoming GitHub context
- `Knowledge Extraction`: PR review feedback is assembled into extraction input and sent to the LLM-backed extraction stage
- `Reflection`: weekly digest generation summarizes workspace-scoped learnings into a reusable review artifact
- `Lifecycle Control`: scheduled retention tasks clean up raw PR source data and enforce longer-lived digest or learning retention policies over time

Operationally, these stages are split across dedicated Celery lanes so heavy cleanup or digest work does not block webhook-driven extraction.

## データ取扱い概要

PR Knowledge Hub は、認証情報、workspace、GitHub 接続情報、repository、pull request、review comment、learning item、weekly digest をアプリケーションのデータベースに保存します。Celery のキューと結果管理には Redis を使い、ローカルまたはセルフホスト前提の LLM 接続先として Ollama を利用できます。

外部送信は、GitHub から PR 情報を取得するとき、または LLM プロバイダを呼び出すときに限られます。GitHub API へのアクセスには GitHub App または token 接続を使います。Anthropic を使う場合は抽出・生成用のプロンプトが Anthropic に送信されます。Ollama を使う場合は `OLLAMA_BASE_URL` にのみ送信されます。

保持期間とデータ最小化の既定方針は [docs/data-handling-policy.md](/C:/Users/s141142/Desktop/myenv/LT_oosaka/docs/data-handling-policy.md) に記載しています。この文書では、現状実装の事実、運用方針としての既定値、今後の強化項目を分けて整理しています。

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
alembic -c migrations/alembic.ini upgrade head
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

Demo data:

```bash
cd api
python scripts/seed_demo_data.py
```

This creates a loginable demo account:

- Email: `demo@example.com`
- Password: `demo12345`

## Testing

Backend:

```bash
cd api
pytest -q
```

Frontend build:

```bash
cd web
npm run build
```

Current local verification at the time of the latest refactor:

- `api`: `123 passed`
- `web`: lint passes before build in CI
- `web`: production build succeeds

## CI

GitHub Actions runs:

- `api`: `pytest -q`
- `web`: `npm ci && npm run lint && npm run build`

Workflow file:

- `.github/workflows/ci.yml`

## Main User Flow

1. Register or log in at `/login`.
2. Use the default personal workspace.
3. Connect GitHub through the backend integration endpoints.
4. Receive webhook-driven PR ingestion and extraction.
5. Review learning items on `/learning-items`.
6. Generate and read workspace-scoped digests on `/weekly-digests`.
7. Reanalyze an existing PR through the API, executed asynchronously by Celery.

## Development Notes

- The fixture-backed `/analyze` router is intentionally excluded from `app.main:app`.
- `api/fixtures/` is a development and test aid for extraction behavior, not a production API surface.
- `web` CI runs both `npm run lint` and `npm run build`.
- Webhook, Celery, and digest logs include stable tracing fields such as `event_type`, `action`, `workspace_id`, `pr_number`, `installation_id`, `pr_id`, `year`, and `week`.
- 直近の実装修正や判断メモは `CHANGE_SUMMARY.md` に記録しています。

## Key Decisions Reflected in the Current Code

- `workspace` is the primary ownership boundary.
- Weekly digests are listed and generated by `workspace_id`.
- Heavy background work uses Celery instead of FastAPI `BackgroundTasks`.
- The pipeline is split into webhook ingestion, PR processing, learning extraction, digest generation, and scheduled cleanup stages.
- LLM providers implement a common `BaseLLMProvider` contract.
- Tests are aligned to current contracts rather than internal call-count details.

## Required Environment Variables

Defined in `.env.example`:

- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `OLLAMA_BASE_URL`
- `SECRET_KEY`
- `PR_RETENTION_DAYS`
- `LOG_RETENTION_DAYS`
- `LEARNING_RETENTION_DAYS`
- `DIGEST_RETENTION_DAYS`
- `GITHUB_CONNECTION_TOKEN_ENCRYPTION_KEY`
- `APP_ENV`
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
