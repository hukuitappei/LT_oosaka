# Decision Log

## Current Project Direction

This file records the decisions that are still active in the codebase. It is intentionally shorter than a historical design journal.

## Decision 1: Workspace Is the Ownership Boundary

- Status: active
- Decision: repositories, learning items, and weekly digests are owned by `workspace`
- Reason: the product already uses workspace-aware dependencies and membership checks
- Consequence: `user` should be treated as the actor, not the primary data owner

Affected areas:

- `api/app/dependencies.py`
- `api/app/routers/workspaces.py`
- `api/app/routers/weekly_digests.py`
- `api/app/services/digest_generator.py`

## Decision 2: Heavy Background Work Uses Celery

- Status: active
- Decision: webhook extraction, digest generation, and PR reanalysis should run through Celery
- Reason: retry, failure visibility, and operational consistency are better than request-local background execution
- Consequence: FastAPI routes should enqueue work instead of executing heavy tasks inline

Affected areas:

- `api/app/tasks/extract.py`
- `api/app/routers/pull_requests.py`
- `api/app/celery_app.py`

## Decision 3: LLM Providers Must Share a Common Contract

- Status: active
- Decision: providers implement `BaseLLMProvider`, including `generate_text`
- Reason: digest generation should not depend on provider-specific type checks
- Consequence: provider switching stays inside the provider layer

Affected areas:

- `api/app/llm/base.py`
- `api/app/llm/anthropic_provider.py`
- `api/app/llm/ollama_provider.py`
- `api/app/services/digest_generator.py`

## Decision 4: Tests Should Follow Contracts, Not Internal Call Details

- Status: active
- Decision: tests should validate observable behavior and data contracts rather than fragile mock call counts
- Reason: recent failures came from outdated assumptions, not from core feature regressions
- Consequence: service and router tests should remain resilient to internal refactors

Affected areas:

- `api/tests/test_digest_generator.py`
- `api/tests/test_learning_saver.py`
- `api/tests/test_pr_processor.py`
- `api/tests/test_preprocessor.py`
- `api/tests/test_webhook_and_digest.py`

## Decision 5: CI Is the Minimum Quality Gate

- Status: active
- Decision: every change should at least pass backend tests and frontend production build
- Reason: these two checks catch the majority of current breakage modes
- Consequence: CI is required before trusting documentation or merge readiness
- Additional note: the `web` job now runs `npm run lint` before `npm run build`

Affected areas:

- `.github/workflows/ci.yml`
- `api/`
- `web/`

## Decision 6: Fixture Analysis Stays Out Of The Main App

- Status: active
- Decision: fixture-backed PR analysis routes should not be mounted in `app.main:app`
- Reason: they are useful for local inspection, but they are not part of the production user flow
- Consequence: fixture samples remain available for tests and ad hoc development, but the main startup path stays focused on the real product surface

Affected areas:

- `api/app/main.py`
- `api/app/routers/analyze.py`
- `api/fixtures/`
- `api/tests/test_main_app.py`

## Decision 7: Background Work Uses Structured Context Logs

- Status: active
- Decision: webhook ingestion, Celery tasks, and digest generation should log stable identifiers for tracing
- Reason: failures are easier to triage when `event_type`, `action`, `workspace_id`, `pr_number`, `installation_id`, `pr_id`, `year`, and `week` are emitted consistently
- Consequence: operational logs should stay structured and avoid ad hoc wording that hides the important identifiers

Affected areas:

- `api/app/routers/webhook.py`
- `api/app/tasks/extract.py`
- `api/app/services/pr_processor.py`
- `api/app/services/digest_generator.py`

## Known Transitional State

These are acknowledged but not yet fully resolved:

- some service and query logic is still spread across routers and services
- Docker Compose was not verified in the latest environment because Docker was unavailable there
