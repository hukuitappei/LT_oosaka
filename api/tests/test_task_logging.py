import logging
from collections.abc import Coroutine

import pytest


def _drain_coroutine_and_return(result):
    def runner(coro: Coroutine):
        coro.close()
        return result

    return runner


@pytest.mark.asyncio
async def test_extract_pr_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import extract_pr_task

    payload = {
        "action": "created",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 42},
        "installation": {"id": 999},
    }

    monkeypatch.setattr(
        "app.tasks.extract.asyncio.run",
        _drain_coroutine_and_return({"status": "ok", "pr_number": 42}),
    )

    with caplog.at_level(logging.INFO):
        result = extract_pr_task.__wrapped__(payload)

    assert result == {"status": "ok", "pr_number": 42}
    assert any(
        "extract_pr_task started attempt=1 action=created repo=owner/repo pr_number=42 installation_id=999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "extract_pr_task completed attempt=1 action=created repo=owner/repo pr_number=42 installation_id=999 status=ok"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_reanalyze_pr_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import reanalyze_pr_task

    monkeypatch.setattr(
        "app.tasks.extract.asyncio.run",
        _drain_coroutine_and_return({"status": "ok", "pr_id": 42}),
    )

    with caplog.at_level(logging.INFO):
        result = reanalyze_pr_task.__wrapped__(42, 3, 7)

    assert result == {"status": "ok", "pr_id": 42}
    assert any(
        "reanalyze_pr_task started attempt=1 pr_id=42 workspace_id=3 user_id=7" in record.message
        for record in caplog.records
    )
    assert any(
        "reanalyze_pr_task completed attempt=1 pr_id=42 workspace_id=3 user_id=7 status=ok"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_generate_digest_task_logs_context(monkeypatch, caplog):
    from app.tasks.extract import generate_digest_task

    monkeypatch.setattr(
        "app.tasks.extract.asyncio.run",
        _drain_coroutine_and_return({"status": "ok", "digest_id": 7}),
    )

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
