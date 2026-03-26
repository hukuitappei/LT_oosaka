# PR Knowledge Hub

PR Knowledge Hub is a monorepo for turning pull request review feedback into reusable learning items and weekly digests.

The current production path is the `api/` FastAPI backend plus the `web/` Next.js frontend.

## What It Does

- Ingests GitHub pull request and webhook data
- Extracts structured learning items from review feedback
- Stores repositories, pull requests, workspaces, and weekly digests
- Shows a dashboard for recent learnings and digest summaries
- Supports email/password auth and GitHub OAuth / GitHub App connections

## Architecture

- `web/` is the Next.js app used by end users
- `api/` is the FastAPI backend that serves auth, workspaces, repositories, pull requests, learning items, weekly digests, and webhook endpoints
- `worker` runs Celery jobs for async processing
- `db` is PostgreSQL in Docker Compose, or SQLite for lighter local development
- `cache` is Redis for Celery
- `llm` is Ollama for local model access

The frontend talks to the backend through `API_URL`. In local development that defaults to `http://localhost:8000`. In Docker Compose it is set to `http://api:8000`.

## Quick Start

### Docker Compose

1. Copy `.env.example` to `.env` and fill in the required secrets.
2. Start the stack:

```bash
docker compose up --build
```

3. Open:
- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Local Development

Backend:

```bash
pip install -r api/requirements.txt
cd api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd web
npm install
npm run dev
```

For the full feature set, you still need Redis, PostgreSQL, and an LLM backend available. The backend can fall back to the SQLite default from `.env.example` for simpler local work, but GitHub and digest flows expect the rest of the stack to be configured.

## Required Environment Variables

Defined in `.env.example`:

- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `OLLAMA_BASE_URL`
- `SECRET_KEY`
- `APP_ENV`
- `CORS_ORIGINS`
- `GITHUB_APP_ID`
- `GITHUB_PRIVATE_KEY`
- `GITHUB_WEBHOOK_SECRET`
- `GITHUB_OAUTH_CLIENT_ID`
- `GITHUB_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI`

Notes:

- `DATABASE_URL` defaults to SQLite for local development.
- `SECRET_KEY` should be replaced before any shared or deployed use.
- GitHub App and OAuth variables are only required when those integrations are enabled.

## Main User Flow

1. Register or log in at `/login`.
2. Select or create a workspace.
3. Connect GitHub through the backend integration endpoints.
4. Review extracted learning items on the home dashboard and `/learning-items`.
5. Open weekly summaries on `/weekly-digests` and `/weekly-digests/[id]`.
6. Use the backend webhook and async worker path to keep PR data and digests up to date.

## Current Limitations

- GitHub integrations are not fully usable without the corresponding app or OAuth secrets.
- LLM-based extraction depends on either Anthropic or Ollama being configured.
- The repository currently has separate backend and frontend startup paths, so both need to be kept in sync when changing auth, workspace, or API contracts.
