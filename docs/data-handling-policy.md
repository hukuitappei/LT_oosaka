# Data Handling Policy

This document describes what data PR Knowledge Hub stores, what it keeps only in transit, and how retention windows are applied.

## What We Store

The application currently persists its core product data in PostgreSQL.

- User records: email, password hash, GitHub user ID, GitHub login, active flag
- Workspace and membership records: workspace name, slug, personal workspace flag, member role
- GitHub connection records: provider type, workspace ID, user ID, installation ID, encrypted access token where applicable, GitHub account login, label, active flag
- Repository and pull request records: GitHub repository ID, repository name, PR number, title, body, state, author, GitHub URL, merged timestamp, processed flag
- Review comment records: GitHub comment ID, author, body, file path, line number, diff hunk, resolved flag
- Learning records: title, detail, category, confidence, evidence, next action, visibility, schema version
- Weekly digest records: summary, repeated issues, next-time notes, PR count, learning count, visibility

PostgreSQL also contains operational metadata used by the app and background jobs.

- Redis is used as the Celery broker and task result backend.
- Ollama is used when `OLLAMA_BASE_URL` is configured.
- Application logs may include event type, action, workspace ID, PR number, installation ID, and correlation identifiers.

## What We Do Not Persist

The following data is intentionally not stored as a primary persistent artifact in the current codebase.

- Raw webhook payloads are processed in memory and not persisted in full.
- GitHub access tokens and installation secrets are not exposed in plaintext in application responses.
- Prompt inputs are assembled for extraction and digest generation, but nonessential repository or account metadata is not added to prompts.

## Retention Windows

The project uses explicit retention windows for cleanup jobs and purge actions.

| Data Type | Default Retention | Notes |
| --- | --- | --- |
| GitHub access token and connection secrets | Keep only while the connection is active | Removed when the connection is deleted or invalidated |
| Raw webhook payloads | Not retained | Processed in memory only |
| Pull request / review comment derived data | 90 days | Keep enough for review follow-up and cleanup jobs |
| Learning item / weekly digest | 1 year | Longer-lived than raw review artifacts |
| Application logs | 30 days | Operational logs are retained separately from product data |

## Cleanup Model

- `workspace` is the primary ownership boundary.
- Retention jobs clean up expired raw data on a schedule.
- The workspace purge flow deletes repositories, pull requests, review comments, learning items, weekly digests, GitHub connections, and memberships for the target workspace.
- Log retention is independent from product-data retention.

## External Services

Data may flow through the following external systems:

- GitHub API: repository, pull request, review comment, and review metadata lookups
- Anthropic API: prompt submission for extraction and digest generation
- Ollama: local model inference when `OLLAMA_BASE_URL` is configured

## Operational Notes

- Workspace-scoped ownership is the default model.
- Sensitive data should be minimized in logs and prompts.
- Purge flows require an explicit workspace slug confirmation.
- Retention and cleanup behavior should be kept aligned with the service-layer contracts and the scheduled cleanup jobs.
