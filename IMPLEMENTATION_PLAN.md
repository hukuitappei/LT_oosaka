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

## Priority Execution Plan

### Priority 1: Improve Related Learning Recommendation Quality

Current state:
- Related learning suggestions already exist on the PR detail page.
- Ranking has moved beyond simple token overlap, but it still needs to become a stable and trusted recommendation surface.
- The product is strongest when it returns the right prior learning at the exact review moment where it can prevent repetition.

Change:
- Continue improving ranking with richer signals such as repository fit, category alignment, status, confidence, recency, review comment context, and file path context.
- Keep returning recommendation explanations and relevance metadata from the API so the UI can explain the ordering.
- Maintain service-level ranking tests and UI/E2E coverage for recommendation metadata and match types.

Expected result:
- Suggestions become easier to trust because the product can explain why they were surfaced.
- Ranking moves closer to "what is most useful to avoid repeating now" instead of "what shares words."
- This strengthens the product's differentiation around carrying review knowledge forward.

Implementation scope:
- backend ranking improvements in `api/app/services/pull_requests.py`
- related recommendation response fields in `api/app/routers/pull_requests.py`
- PR detail rendering in `web/src/app/pull-requests/[id]/page.tsx`
- frontend type alignment in `web/src/lib/api.ts`
- targeted regression and ranking tests in `api/tests/`

Review and test standard:
- ranking behavior must be covered by explicit test cases
- response changes must preserve existing fields and add explanation metadata safely
- UI must render recommendation reasons and match types without breaking the existing PR detail flow
- backend tests and frontend build must pass before closing the task

### Priority 2: Split Recommendation Work into Multi-Step AI/Service Roles

Current state:
- Extraction and recommendation are implemented, but recommendation quality improvements currently require changing one service in one place.
- The system is operational, yet there is limited separation between extraction, consolidation, and recommendation responsibilities.

Change:
- Separate recommendation work into stages such as extraction, deduplication, recurrence detection, and ranking.
- Keep each stage observable and testable on its own, even if some stages remain heuristic before using more AI.

Expected result:
- Quality issues become easier to isolate and improve.
- Future AI-assisted recommendation work can be introduced incrementally without destabilizing the existing extraction flow.
- This raises the project's swarm-orchestration maturity in practical terms.

### Priority 3: Measure Reuse and Impact in Real Workflows

Current state:
- Learning items can be created, searched, reviewed, and status-tracked.
- The system supports activation, but it does not yet prove whether a learning item reduced repeat review feedback.

Change:
- Track where learning items are reused and whether similar review comments decrease after adoption.
- Surface adoption and recurrence metrics in digest/reporting flows.

Expected result:
- The product can show not only that users interacted with learning items, but that those learnings affected engineering outcomes.
- This improves practical adoption and gives teams a clearer reason to keep the workflow in place.

## Execution Order

1. Finish Priority 1 end-to-end with implementation, review, and test evidence.
2. Validate recommendation quality against real PR data.
3. Move to Priority 2 once the recommendation surface is stable.
4. Add Priority 3 after reuse signals are available in production flows.

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
