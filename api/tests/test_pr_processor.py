import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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


@pytest.mark.asyncio
async def test_process_pr_event_skips_if_already_processed():
    """PR が processed=True の場合、学習抽出をスキップする（冪等性）"""
    from app.services.pr_processor import process_pr_event

    mock_db = AsyncMock()

    # Mock existing processed PR
    mock_repo = MagicMock()
    mock_repo.id = 1
    mock_pr = MagicMock()
    mock_pr.processed = True
    mock_pr.github_pr_number = 42

    mock_db.scalar = AsyncMock(side_effect=[mock_repo, mock_pr])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    payload = _make_webhook_payload()

    with patch("app.services.pr_processor.extract_from_pr") as mock_extract:
        await process_pr_event(payload, mock_db)
        mock_extract.assert_not_called()


@pytest.mark.asyncio
async def test_process_pr_event_creates_repository_if_not_exists():
    """リポジトリが存在しない場合は新規作成される"""
    from app.services.pr_processor import process_pr_event
    from app.config import settings

    mock_db = AsyncMock()

    # First scalar (repo lookup) returns None, second (PR lookup) returns None
    mock_db.scalar = AsyncMock(side_effect=[None, None])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)

    payload = _make_webhook_payload()

    # No LLM configured → extraction skipped
    with patch.object(settings, "anthropic_api_key", ""), \
         patch.object(settings, "ollama_base_url", ""):
        await process_pr_event(payload, mock_db)

    # Should have added both a Repository and a PullRequest
    from app.db.models import Repository, PullRequest
    added_types = [type(obj).__name__ for obj in added_objects]
    assert "Repository" in added_types
    assert "PullRequest" in added_types


@pytest.mark.asyncio
async def test_process_pr_event_reuses_existing_repository():
    """リポジトリが既に存在する場合は新規作成しない"""
    from app.services.pr_processor import process_pr_event
    from app.config import settings

    mock_db = AsyncMock()

    # Existing repo found, new PR
    mock_repo = MagicMock()
    mock_repo.id = 10
    mock_db.scalar = AsyncMock(side_effect=[mock_repo, None])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)

    payload = _make_webhook_payload()

    with patch.object(settings, "anthropic_api_key", ""), \
         patch.object(settings, "ollama_base_url", ""):
        await process_pr_event(payload, mock_db)

    from app.db.models import Repository
    added_types = [type(obj).__name__ for obj in added_objects]
    # Repository should NOT be added again
    assert "Repository" not in added_types
    # PullRequest should be created
    assert "PullRequest" in added_types


@pytest.mark.asyncio
async def test_process_pr_event_no_extraction_without_llm_config():
    """LLM の設定がない場合は学習抽出を実行しない"""
    from app.services.pr_processor import process_pr_event
    from app.config import settings

    mock_db = AsyncMock()
    mock_repo = MagicMock()
    mock_repo.id = 1
    mock_pr = MagicMock()
    mock_pr.processed = False
    mock_pr.github_pr_number = 42

    mock_db.scalar = AsyncMock(side_effect=[mock_repo, mock_pr])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    payload = _make_webhook_payload()

    with patch.object(settings, "anthropic_api_key", ""), \
         patch.object(settings, "ollama_base_url", ""), \
         patch("app.services.pr_processor.extract_from_pr") as mock_extract:
        await process_pr_event(payload, mock_db)
        mock_extract.assert_not_called()
