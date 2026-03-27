import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_webhook_payload(pr_number: int = 42, repo_id: int = 100) -> dict:
    return {
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
    from app.services.pr_processor import process_pr_event
    from app.config import settings

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())

    mock_connection = _make_workspace_connection()
    mock_repo = MagicMock(id=1)
    mock_pr = MagicMock()
    mock_pr.processed = True
    mock_pr.github_pr_number = 42
    mock_pr.repository_id = 1

    mock_db.scalar = AsyncMock(side_effect=[mock_connection, mock_repo, mock_pr])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        await process_pr_event(payload, mock_db)

    mock_db.add.assert_not_called()
    mock_db.commit.assert_called_once()
    assert mock_pr.processed is True


@pytest.mark.asyncio
async def test_process_pr_event_creates_repository_if_not_exists():
    from app.services.pr_processor import process_pr_event
    from app.config import settings

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
    from app.services.pr_processor import process_pr_event
    from app.config import settings

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
    from app.services.pr_processor import process_pr_event
    from app.config import settings

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=_make_workspace())

    mock_repo = MagicMock()
    mock_repo.id = 1
    mock_pr = MagicMock()
    mock_pr.processed = False
    mock_pr.github_pr_number = 42
    mock_pr.repository_id = 1

    mock_db.scalar = AsyncMock(side_effect=[_make_workspace_connection(), mock_repo, mock_pr])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    payload = _make_webhook_payload()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
        monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)
        await process_pr_event(payload, mock_db)

    mock_db.add.assert_not_called()
    mock_db.commit.assert_called_once()
    assert mock_pr.processed is False
