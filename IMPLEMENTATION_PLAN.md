# Implementation Plan

## Status

The project is past the initial MVP stage. The current codebase supports:

- authentication and personal workspaces
- workspace-scoped repository and learning data
- GitHub webhook ingestion
- LLM extraction of learning items
- weekly digest generation
- Celery-based async jobs
- a working Next.js frontend
- backend tests and frontend production build checks
- structured tracing logs for webhook, Celery, and digest workflows

## Completed Milestones

### Phase 1: Repository and Runtime Setup

- monorepo structure created
- Next.js, FastAPI, PostgreSQL, Redis, Celery, and Ollama compose setup
- health endpoints and base app wiring

### Phase 2: Extraction MVP

- fixture-based PR analysis flow
- prompt building and LLM schema validation
- learning item persistence

Current status: the fixture-backed analysis path is retained as a development/testing aid, but it is not mounted in the main FastAPI app.

### Phase 3: GitHub Ingestion

- GitHub webhook endpoint
- PR and review comment ingestion path
- repository / PR persistence

### Phase 4: LLM Abstraction

- provider abstraction through `BaseLLMProvider`
- Anthropic and Ollama providers
- retry-aware extraction flow

### Phase 5: Weekly Digest

- weekly digest model and endpoints
- digest generation from learning items
- digest UI pages

### Phase 6: Auth and Workspace Context

- email/password auth
- personal workspaces
- workspace-aware dependencies
- frontend login flow

### Phase 7: Reliability and Refactor

- Celery tasks for extraction and digest generation
- API container migration on startup
- provider-level `generate_text` support
- retry logic for digest generation
- PR processed flag for duplicate suppression
- CI for backend tests and frontend build
- digest flow refactored to be workspace-centric
- PR reanalysis moved to Celery
- router/service boundaries tightened for PR reanalysis and weekly digest flows
- workspace membership queries and updates moved behind service APIs
- backend tests updated to current contracts

## Current Architecture Direction

### Domain

- `workspace` is the primary ownership boundary
- `user` is the authentication actor
- digest generation and listing are workspace-scoped

### Service Boundaries

- routers should stay focused on auth, request parsing, and HTTP errors
- service modules should own workspace-scoped queries and orchestration
- route and service tests should be split when they fail for different reasons

### Async

- webhook ingestion, digest generation, and PR reanalysis use Celery
- heavy work should stay out of FastAPI request handlers

### Development Surface

- fixture-backed `/analyze` routes are excluded from `app.main:app`
- `api/fixtures/` remains available for local inspection and tests

### Quality

- backend quality gate: `pytest -q`
- frontend quality gate: `npm run lint` followed by `npm run build`
- CI enforces both on push and pull request

## Remaining Work

### High Priority

1. Continue moving remaining route-owned query/orchestration logic behind service APIs.
2. Add one end-to-end flow covering register/login/workspace/learning-items/digest.
3. Extract auth session and GitHub OAuth orchestration from `api/app/routers/auth.py`.

### Medium Priority

1. Decide whether Docker Compose or local scripts are the primary development path.
2. Add better observability for Celery task failures and webhook processing.
3. Tighten GitHub connection flows and repository synchronization UX.

### Low Priority

1. Expand integrations beyond PR review comments.
2. Add team collaboration polish beyond the current workspace baseline.
3. Revisit long-term orchestration if Celery becomes limiting.

## Working Definition of Done

A change is considered done when:

- backend tests pass
- frontend production build passes
- workspace ownership rules remain consistent
- async work is routed through Celery where appropriate
- README and decision records remain aligned with the implementation
