# Staging Verification Checklist

Use this checklist before treating GitHub, webhook, or deployment behavior as verified in an environment close to production.

## Current Status

- As of 2026-04-07, local code verification is in place for the core control paths behind this checklist.
- Local verification passed with:
  - `pytest -q api/tests/test_auth_router.py api/tests/test_workspace_access.py api/tests/test_github_connections_router.py api/tests/test_github_connections_service.py api/tests/test_repositories_router.py api/tests/test_pr_processor.py api/tests/test_webhook.py api/tests/test_task_logging.py`
  - Result: `48 passed`
  - `npm run test:e2e -- --grep auth`
  - Result: `5 passed`
- Remaining work is staging-only validation against real GitHub, real webhook delivery, real worker execution, and deployed cookie / proxy behavior.

## Recommended Execution Order

1. Runtime and proxy baseline
2. GitHub OAuth
3. GitHub App linking
4. Real webhook delivery and Celery processing
5. Repository sync and degraded-permission behavior

Do not start webhook or repository-sync validation before confirming the staging hostname, cookies, reverse proxy, `API_URL`, and worker connectivity.

## Preconditions

- `API_URL`, auth cookie settings, and reverse-proxy behavior are configured for staging.
- GitHub OAuth credentials are valid for the staging callback URL.
- A GitHub App installation exists for at least one test repository.
- Redis, PostgreSQL, and the worker process are running.
- At least one test workspace and one test repository are available.

### Preflight Notes

- The web app proxies backend requests through `web/src/app/api/backend/[...path]/route.ts`, so staging `API_URL` must target the staging backend, not localhost.
- Browser auth depends on the `token` and `workspace_id` cookies being readable by the deployed frontend paths.
- Webhook signature verification is strict outside development. Staging must have `APP_ENV` set away from `development` and must provide `GITHUB_WEBHOOK_SECRET`.
- PR ingestion only resolves a workspace when a real active GitHub App connection exists for the incoming `installation_id`.

### Evidence From Local Code

- Runtime / cookie / workspace context
  - Client login stores `token` and `workspace_id` in both local storage and cookies.
  - Server-rendered requests also read `token` and `workspace_id` from cookies.
  - Frontend auth navigation, protected-route redirects, logout, and GitHub connection UI flows pass in Playwright.
- OAuth
  - Backend has `/auth/github/start` and `/auth/github/callback`.
  - Callback failure modes already map to explicit 400 responses for not-configured, token exchange failure, and missing email.
- GitHub App linking
  - App installation linking is workspace-scoped and restricted to `owner` / `admin`.
  - Re-linking the same installation in the same workspace reactivates and updates the existing record.
  - Delete requires the same workspace admin permission gate.
- Webhook / Celery
  - Signature validation is enforced when not in development.
  - Supported PR-related events are enqueued to Celery rather than processed inline.
  - Logs include stable fields such as `event_type`, `action`, `repo`, `pr_number`, `installation_id`, and `correlation_id`.
- Repository sync
  - PR ingestion upserts repository and PR rows after resolving workspace from the active GitHub App installation mapping.
  - If no workspace mapping is found, the event is skipped with a warning instead of being applied to the wrong workspace.

## GitHub OAuth

- Start the OAuth flow from the UI.
- Confirm the callback lands on the expected redirect URI.
- Verify the session cookie is set and accepted by the frontend.
- Confirm the default workspace context is resolved correctly after login.
- Repeat the flow with an invalid or revoked credential and confirm the failure is clear.

### Staging Actions

- Open the staging login page and initiate the GitHub OAuth entrypoint that targets `/auth/github/start`.
- Inspect the redirect target and confirm it matches the exact deployed callback URL configured in `GITHUB_OAUTH_REDIRECT_URI`.
- After callback, confirm:
  - the browser has `token` and `workspace_id`
  - authenticated navigation to `/` succeeds without redirecting back to `/login`
  - API requests sent through `/api/backend/...` succeed under the same session
- Run a negative test by temporarily using an invalid code path or revoked client secret and confirm the UI or API exposes a clear failure message instead of a loop or blank screen.

## GitHub App Linking

- Link a GitHub App installation to the target workspace.
- Confirm the installation ID is stored and visible in the connection list.
- Verify the workspace permission model matches the intended `owner/admin only` policy.
- Delete the connection and confirm the app link is removed cleanly.
- Re-link the same installation and confirm the flow is idempotent or fails with a clear reason.

### Staging Actions

- In a workspace where the acting user is `owner` or `admin`, open `/github-connections` and register a real GitHub App installation ID.
- Confirm the resulting connection card shows the expected installation ID and remains visible after refresh.
- Repeat from a non-admin member account and confirm the API returns `403 Insufficient workspace permissions`.
- Delete the connection from an admin account and confirm the record disappears from the list.
- Re-link the same installation ID and confirm the same connection is reactivated or the failure reason is explicit and stable.

## Webhook Delivery

- Deliver a real GitHub webhook event into staging.
- Confirm signature validation succeeds.
- Confirm the event is enqueued to Celery and not executed inline.
- Verify the PR processing logs include stable tracing fields.
- Send a malformed payload and confirm the failure is observable without exposing sensitive data.

### Staging Actions

- Configure the GitHub App webhook to point at the staging `/webhooks/github` endpoint with the same secret as `GITHUB_WEBHOOK_SECRET`.
- Trigger a real supported event:
  - merged `pull_request`
  - submitted `pull_request_review`
  - created or edited `pull_request_review_comment`
- Confirm in logs that the request path shows:
  - signature accepted
  - `Webhook stage=handoff`
  - `Webhook enqueued Celery task`
  - subsequent `extract_pr_task started`
- Verify the HTTP response is fast and does not wait for downstream extraction completion.
- Send a malformed signature or malformed payload and confirm the failure is observable as `401` or validation failure without dumping secrets or raw credentials into logs.

## Repository Sync

- Sync a test repository from GitHub into the workspace.
- Confirm repository visibility matches the installation permissions.
- Confirm PR ingestion creates or updates the expected repository and PR records.
- Revoke access to the installation and verify the UI or API reports the degraded state clearly.

### Staging Actions

- Use a repository that is actually included in the linked installation permissions.
- Trigger a supported webhook from that repository and confirm:
  - the repository appears under the intended workspace
  - the PR appears under that repository
  - a repeat event updates existing rows rather than duplicating them
- Remove the repository or installation access in GitHub and confirm the next sync attempt or webhook path yields a clear degraded-state signal in UI or API behavior.
- Confirm no unrelated workspace receives the repository or PR when installation scope changes.

## Runtime and Proxy

- Confirm login, logout, and authenticated page navigation work through the staging hostname.
- Confirm cookies are accepted by the browser with the deployed domain and path settings.
- Verify `API_URL` points to the staging backend and not a local development endpoint.
- Confirm static assets and API requests both succeed behind the reverse proxy.

### Staging Actions

- Open the deployed hostname directly, not a local tunnel, and walk through login, homepage load, `/github-connections`, and logout.
- In browser devtools, verify:
  - `token` and `workspace_id` cookies are present on the staging domain
  - requests to `/api/backend/...` are forwarded to the staging backend
  - no request attempts `localhost:8000` or another development host
- Confirm static assets load from the deployed web origin and API responses return through the reverse proxy without mixed-origin breakage.
- Confirm logout clears the auth cookies and protected routes redirect back to `/login`.

## Acceptance Criteria

- OAuth login works end to end.
- GitHub App linking works end to end.
- Webhook delivery triggers Celery-backed processing.
- Repository sync reflects real GitHub permissions.
- Deployment-time cookie and proxy behavior match the intended flow.
- Failures are visible in logs and do not require guessing at the root cause.
