# Staging Verification Checklist

Use this checklist before treating GitHub, webhook, or deployment behavior as verified in an environment close to production.

## Preconditions

- `API_URL`, auth cookie settings, and reverse-proxy behavior are configured for staging.
- GitHub OAuth credentials are valid for the staging callback URL.
- A GitHub App installation exists for at least one test repository.
- Redis, PostgreSQL, and the worker process are running.
- At least one test workspace and one test repository are available.

## GitHub OAuth

- Start the OAuth flow from the UI.
- Confirm the callback lands on the expected redirect URI.
- Verify the session cookie is set and accepted by the frontend.
- Confirm the default workspace context is resolved correctly after login.
- Repeat the flow with an invalid or revoked credential and confirm the failure is clear.

## GitHub App Linking

- Link a GitHub App installation to the target workspace.
- Confirm the installation ID is stored and visible in the connection list.
- Verify the workspace permission model matches the intended `owner/admin only` policy.
- Delete the connection and confirm the app link is removed cleanly.
- Re-link the same installation and confirm the flow is idempotent or fails with a clear reason.

## Webhook Delivery

- Deliver a real GitHub webhook event into staging.
- Confirm signature validation succeeds.
- Confirm the event is enqueued to Celery and not executed inline.
- Verify the PR processing logs include stable tracing fields.
- Send a malformed payload and confirm the failure is observable without exposing sensitive data.

## Repository Sync

- Sync a test repository from GitHub into the workspace.
- Confirm repository visibility matches the installation permissions.
- Confirm PR ingestion creates or updates the expected repository and PR records.
- Revoke access to the installation and verify the UI or API reports the degraded state clearly.

## Runtime and Proxy

- Confirm login, logout, and authenticated page navigation work through the staging hostname.
- Confirm cookies are accepted by the browser with the deployed domain and path settings.
- Verify `API_URL` points to the staging backend and not a local development endpoint.
- Confirm static assets and API requests both succeed behind the reverse proxy.

## Acceptance Criteria

- OAuth login works end to end.
- GitHub App linking works end to end.
- Webhook delivery triggers Celery-backed processing.
- Repository sync reflects real GitHub permissions.
- Deployment-time cookie and proxy behavior match the intended flow.
- Failures are visible in logs and do not require guessing at the root cause.
