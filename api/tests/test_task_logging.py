import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


class _AsyncSessionContext:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_extract_pr_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import extract_pr_task

    payload = {
        "action": "created",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 42},
        "installation": {"id": 999},
        "event_type": "pull_request_review_comment",
    }

    def fake_run(coro):
        coro.close()
        return {"status": "queued", "pr_number": 42}

    monkeypatch.setattr("app.tasks.extract.asyncio.run", fake_run)

    with caplog.at_level(logging.INFO):
        result = extract_pr_task.__wrapped__(payload)

    assert result == {"status": "queued", "pr_number": 42}
    assert any(
        "extract_pr_task started attempt=1 action=created repo=owner/repo pr_number=42 installation_id=999 correlation_id=github-webhook:pull_request_review_comment:created:owner/repo:42:999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "extract_pr_task completed attempt=1 action=created repo=owner/repo pr_number=42 installation_id=999 correlation_id=github-webhook:pull_request_review_comment:created:owner/repo:42:999 status=queued"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_reanalyze_pr_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import reanalyze_pr_task

    def fake_run(coro):
        coro.close()
        return {"status": "queued", "pr_id": 42}

    monkeypatch.setattr("app.tasks.extract.asyncio.run", fake_run)

    with caplog.at_level(logging.INFO):
        result = reanalyze_pr_task.__wrapped__({"pr_id": 42, "workspace_id": 3, "user_id": 7})

    assert result == {"status": "queued", "pr_id": 42}
    assert any(
        "reanalyze_pr_task started attempt=1 pr_id=42 workspace_id=3 user_id=7" in record.message
        for record in caplog.records
    )
    assert any(
        "reanalyze_pr_task completed attempt=1 pr_id=42 workspace_id=3 user_id=7 status=queued"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_generate_digest_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import generate_digest_task

    def fake_run(coro):
        coro.close()
        return {"status": "ok", "digest_id": 7}

    monkeypatch.setattr("app.tasks.extract.asyncio.run", fake_run)

    with caplog.at_level(logging.INFO):
        result = generate_digest_task.__wrapped__(2026, 13, 5)

    assert result == {"status": "ok", "digest_id": 7}
    assert any(
        "generate_digest_task started attempt=1 year=2026 week=13 workspace_id=5" in record.message
        for record in caplog.records
    )
    assert any(
        "generate_digest_task completed attempt=1 year=2026 week=13 workspace_id=5 status=ok"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_generate_scheduled_weekly_digests_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import generate_scheduled_weekly_digests_task

    def fake_run(coro):
        coro.close()
        return {
            "status": "ok",
            "year": 2026,
            "week": 12,
            "workspace_count": 4,
            "generated_count": 4,
        }

    monkeypatch.setattr("app.tasks.extract.asyncio.run", fake_run)

    with caplog.at_level(logging.INFO):
        result = generate_scheduled_weekly_digests_task.__wrapped__()

    assert result["status"] == "ok"
    assert any(
        "generate_scheduled_weekly_digests_task started attempt=1" in record.message
        for record in caplog.records
    )
    assert any(
        "generate_scheduled_weekly_digests_task completed attempt=1 year=2026 week=12 workspace_count=4 generated_count=4 status=ok"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_extract_learning_items_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import extract_learning_items_task

    request = {
        "workspace_id": 5,
        "pr_id": 42,
        "repo": "owner/repo",
        "pr_number": 42,
        "installation_id": 999,
        "correlation_id": "github-webhook:pull_request:closed:owner/repo:42:999",
        "pr_dict": {"title": "x"},
    }

    def fake_run(coro):
        coro.close()
        return {"status": "ok", "pr_id": 42, "learning_count": 2}

    monkeypatch.setattr("app.tasks.extract.asyncio.run", fake_run)

    with caplog.at_level(logging.INFO):
        result = extract_learning_items_task.__wrapped__(request)

    assert result["status"] == "ok"
    assert any(
        "extract_learning_items_task started attempt=1 workspace_id=5 pr_id=42 repo=owner/repo pr_number=42 installation_id=999 correlation_id=github-webhook:pull_request:closed:owner/repo:42:999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "extract_learning_items_task completed attempt=1 workspace_id=5 pr_id=42 repo=owner/repo pr_number=42 installation_id=999 correlation_id=github-webhook:pull_request:closed:owner/repo:42:999 status=ok"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_cleanup_retention_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import cleanup_retention_task

    def fake_run(coro):
        coro.close()
        return {
            "status": "ok",
            "deleted_pull_requests": 2,
            "deleted_review_comments": 4,
            "detached_learning_items": 3,
            "deleted_expired_learning_items": 1,
            "deleted_weekly_digests": 2,
            "pr_source_cutoff": "2026-01-01T00:00:00+00:00",
            "log_metadata_cutoff": "2026-03-01T00:00:00+00:00",
            "learning_cutoff": "2025-04-07T00:00:00+00:00",
            "digest_cutoff": "2025-04-07T00:00:00+00:00",
            "loki_published": True,
        }

    monkeypatch.setattr("app.tasks.extract.asyncio.run", fake_run)

    with caplog.at_level(logging.INFO):
        result = cleanup_retention_task.__wrapped__()

    assert result["status"] == "ok"
    assert any("cleanup_retention_task started attempt=1" in record.message for record in caplog.records)
    assert any(
        "cleanup_retention_task completed attempt=1 deleted_pull_requests=2 deleted_review_comments=4 detached_learning_items=3 deleted_expired_learning_items=1 deleted_weekly_digests=2 pr_source_cutoff=2026-01-01T00:00:00+00:00 log_metadata_cutoff=2026-03-01T00:00:00+00:00 learning_cutoff=2025-04-07T00:00:00+00:00 digest_cutoff=2025-04-07T00:00:00+00:00 status=ok"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_run_cleanup_retention_does_not_fail_when_loki_publish_errors(monkeypatch):
    from app.schemas.handoffs import RetentionCleanupTaskResult
    from app.tasks import extract as tasks

    class _Cleanup:
        deleted_pull_requests = 1
        deleted_review_comments = 2
        detached_learning_items = 3
        deleted_expired_learning_items = 4
        deleted_weekly_digests = 5

        class window:
            as_of = datetime(2026, 4, 7, 9, 0, 0, tzinfo=timezone.utc)
            pr_source_cutoff = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            log_metadata_cutoff = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
            learning_cutoff = datetime(2025, 4, 7, 0, 0, 0, tzinfo=timezone.utc)
            digest_cutoff = datetime(2025, 4, 7, 0, 0, 0, tzinfo=timezone.utc)

    db = MagicMock()
    monkeypatch.setattr(tasks, "AsyncSessionLocal", lambda: _AsyncSessionContext(db))
    monkeypatch.setattr(tasks, "cleanup_expired_pr_source_data", AsyncMock(return_value=_Cleanup()))
    monkeypatch.setattr(
        tasks,
        "publish_retention_cleanup_result",
        AsyncMock(side_effect=RuntimeError("loki down")),
    )

    result = await tasks._run_cleanup_retention()

    assert result["status"] == "ok"
    assert result["loki_published"] is False


@pytest.mark.asyncio
async def test_run_extract_pr_hands_off_payload_to_processor(monkeypatch):
    from app.tasks import extract as tasks

    payload = {
        "action": "created",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 42},
        "installation": {"id": 999},
        "event_type": "pull_request_review_comment",
    }
    db = MagicMock()
    process_mock = AsyncMock()
    delay_mock = MagicMock()

    monkeypatch.setattr(tasks, "AsyncSessionLocal", lambda: _AsyncSessionContext(db))
    monkeypatch.setattr(tasks, "process_pr_event", process_mock)
    monkeypatch.setattr(tasks, "extract_learning_items_task", MagicMock(delay=delay_mock))
    process_mock.return_value = {
        "workspace_id": 1,
        "pr_id": 99,
        "repo": "owner/repo",
        "pr_number": 42,
        "installation_id": 999,
        "correlation_id": "github-webhook:x",
        "pr_dict": {"title": "x"},
    }

    result = await tasks._run_extract_pr(payload)

    assert result == {"status": "queued", "pr_number": 42}
    process_mock.assert_awaited_once_with(payload, db)
    delay_mock.assert_called_once()


@pytest.mark.asyncio
async def test_run_reanalysis_orchestrates_lookup_and_handoff(monkeypatch, db_session, caplog):
    from app.db.models import PullRequest, Repository, ReviewComment, Workspace
    from app.tasks import extract as tasks

    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve flow",
        body="body",
        state="merged",
        author="alice",
        github_url="https://github.com/owner/repo/pull/42",
    )
    db_session.add(pr)
    await db_session.flush()

    db_session.add(
        ReviewComment(
            pull_request_id=pr.id,
            github_comment_id=1001,
            author="reviewer",
            body="Use a guard clause",
            file_path="app.py",
            line_number=12,
            diff_hunk="@@ -1 +1 @@",
        )
    )
    await db_session.commit()

    delay_mock = MagicMock()

    monkeypatch.setattr(tasks, "AsyncSessionLocal", lambda: _AsyncSessionContext(db_session))
    monkeypatch.setattr(tasks, "extract_learning_items_task", MagicMock(delay=delay_mock))

    with caplog.at_level(logging.INFO):
        result = await tasks._run_reanalysis(pr.id, workspace.id, 7)

    assert result == {"status": "queued", "pr_id": pr.id}
    delay_mock.assert_called_once()
    assert any(
        f"reanalyze_pr_pipeline stage=lookup pr_id={pr.id} workspace_id={workspace.id} user_id=7" in record.message
        for record in caplog.records
    )
    assert any(
        f"reanalyze_pr_pipeline stage=assemble pr_id={pr.id} workspace_id={workspace.id} user_id=7" in record.message
        for record in caplog.records
    )
    assert any(
        f"reanalyze_pr_pipeline stage=extract_handoff pr_id={pr.id} workspace_id={workspace.id} user_id=7" in record.message
        for record in caplog.records
    )
