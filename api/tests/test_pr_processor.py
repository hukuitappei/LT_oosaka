import logging
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_webhook_payload(pr_number: int = 42, repo_id: int = 100) -> dict:
    return {
        "action": "closed",
        "repository": {
            "id": repo_id,
            "full_name": "owner/repo",
            "name": "repo",
        },
        "pull_request": {
            "number": pr_number,
            "title": "Test PR",
            "body": "Test body",
            "state": "closed",
            "user": {"login": "author"},
            "html_url": "https://github.com/owner/repo/pull/42",
        },
        "installation": {"id": 999},
    }


def _make_workspace_connection(workspace_id: int = 1):
    connection = MagicMock()
    connection.workspace_id = workspace_id
    connection.user_id = None
    connection.id = 10
    return connection


def _make_workspace(workspace_id: int = 1):
    workspace = MagicMock()
    workspace.id = workspace_id
    return workspace


@pytest.mark.asyncio
async def test_process_pr_event_skips_if_already_processed():
    from app.config import settings
    from app.services.pr_processor import process_pr_event

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())

    mock_connection = _make_workspace_connection()
    mock_repo = MagicMock(id=1)
    mock_pr = MagicMock()
    mock_pr.processed = True
    mock_pr.github_pr_number = 42

    mock_db.scalar = AsyncMock(side_effect=[mock_connection, mock_repo, mock_pr])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        result = await process_pr_event(payload, mock_db)

    assert result is None
    mock_db.add.assert_not_called()
    mock_db.commit.assert_called_once()
    assert mock_pr.processed is True


@pytest.mark.asyncio
async def test_process_pr_event_creates_repository_if_not_exists():
    from app.config import settings
    from app.services.pr_processor import process_pr_event

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())
    mock_db.scalar = AsyncMock(side_effect=[_make_workspace_connection(), None, None])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        await process_pr_event(payload, mock_db)

    added_types = [type(obj).__name__ for obj in added_objects]
    assert "Repository" in added_types
    assert "PullRequest" in added_types


@pytest.mark.asyncio
async def test_process_pr_event_reuses_existing_repository():
    from app.config import settings
    from app.services.pr_processor import process_pr_event

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())

    mock_repo = MagicMock()
    mock_repo.id = 10
    mock_db.scalar = AsyncMock(side_effect=[_make_workspace_connection(), mock_repo, None])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        await process_pr_event(payload, mock_db)

    added_types = [type(obj).__name__ for obj in added_objects]
    assert "Repository" not in added_types
    assert "PullRequest" in added_types


@pytest.mark.asyncio
async def test_process_pr_event_no_extraction_without_llm_config():
    from app.config import settings
    from app.services.pr_processor import process_pr_event

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())

    mock_repo = MagicMock()
    mock_repo.id = 1
    mock_pr = MagicMock()
    mock_pr.processed = False
    mock_pr.github_pr_number = 42

    mock_db.scalar = AsyncMock(side_effect=[_make_workspace_connection(), mock_repo, mock_pr])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        result = await process_pr_event(payload, mock_db)

    assert result is None
    mock_db.add.assert_not_called()
    mock_db.commit.assert_called_once()
    assert mock_pr.processed is False


@pytest.mark.asyncio
async def test_process_pr_event_returns_extraction_request(caplog):
    from app.config import settings
    from app.services.pr_processor import process_pr_event

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())

    mock_connection = _make_workspace_connection()
    mock_repo = MagicMock()
    mock_repo.id = 1
    mock_pr = MagicMock()
    mock_pr.processed = False
    mock_pr.github_pr_number = 42
    mock_pr.id = 99

    mock_db.scalar = AsyncMock(side_effect=[mock_connection, mock_repo, mock_pr])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        monkeypatch.setattr(
            "app.services.pr_processor._fetch_review_comments",
            AsyncMock(
                return_value=[
                    {
                        "id": 1,
                        "user": {"login": "reviewer"},
                        "body": "guard clause",
                        "path": "app.py",
                        "line": 12,
                        "diff_hunk": "@@ -1 +1 @@",
                    }
                ]
            ),
        )

        with caplog.at_level(logging.INFO):
            result = await process_pr_event(payload, mock_db)

    assert result is not None
    assert result.workspace_id == 1
    assert result.pr_id == 99
    assert result.pr_number == 42
    assert result.repo == "owner/repo"
    assert len(result.pr_dict["review_comments"]) == 1
    assert any(
        "process_pr_event received action=closed repo=owner/repo pr_number=42 installation_id=999" in record.message
        for record in caplog.records
    )
    assert any(
        "process_pr_event stage=workspace_resolution action=closed repo=owner/repo pr_number=42 installation_id=999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "process_pr_event resolved workspace workspace_id=1 action=closed repo=owner/repo pr_number=42 installation_id=999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "process_pr_event stage=repository_upsert workspace_id=1 action=closed repo=owner/repo pr_number=42 installation_id=999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "process_pr_event stage=pull_request_upsert workspace_id=1 action=closed repo=owner/repo pr_number=42 installation_id=999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "process_pr_event stage=extraction_prepare workspace_id=1 action=closed repo=owner/repo pr_number=42 installation_id=999"
        in record.message
        for record in caplog.records
    )
    assert any(
        "process_pr_event prepared extraction workspace_id=1 repo=owner/repo pr_number=42 installation_id=999 review_comment_count=1"
        in record.message
        for record in caplog.records
    )
