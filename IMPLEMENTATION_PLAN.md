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
- learning item search, status tracking, and PR-level related learning suggestions

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
- auth session and GitHub OAuth completion moved behind service APIs
- repository and learning item queries moved behind service APIs
- API-level end-to-end flow added for register/login/workspace/learning-items/digest
- Playwright-based browser E2E smoke flow added for authenticated navigation
- backend tests updated to current contracts

### Phase 8: Learning Activation

- learning item `status` added with `new`, `in_progress`, `applied`, and `ignored`
- learning item list expanded with search, repository filter, PR filter, status filter, and pagination
- learning item summary expanded with `status_counts`
- learning item status updates exposed through `PATCH /learning-items/{id}`
- dashboard and learning item UI updated to support operating on learning items instead of only reading them
- PR detail flow expanded with related learning suggestions from earlier pull requests in the same workspace

## Current Architecture Direction

### Domain

- `workspace` is the primary ownership boundary
- `user` is the authentication actor
- digest generation and listing are workspace-scoped
- learning items are not just records; they are meant to be carried forward into later pull requests

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
- frontend quality gate: `npm run lint`, `npm run build`, and browser E2E for the authenticated flow
- CI enforces both on push and pull request

### Product Direction

- the product should differentiate on reuse of review knowledge, not only storage of extracted learnings
- PR-level related learning suggestions are now part of the intended surface
- dashboard and PR detail views should continue moving toward "what should we avoid repeating next" rather than passive reporting

## Remaining Work

### High Priority

1. Continue moving remaining route-owned query/orchestration logic behind service APIs.
2. Expand related learning suggestions beyond simple token overlap into stronger ranking and recurrence detection.
3. Expand browser E2E beyond the initial smoke path without making the suite brittle.

### Medium Priority

1. Decide whether Docker Compose or local scripts are the primary development path.
2. Add better observability for Celery task failures and webhook processing.
3. Tighten GitHub connection flows and repository synchronization UX.
4. Expose related learning suggestions earlier in the workflow, not only from the PR detail page.

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
