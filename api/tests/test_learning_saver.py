import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_save_learning_items_creates_records(sample_llm_output):
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock(repository_id=123, processed=False)
    mock_repo = MagicMock(workspace_id=456)
    mock_db.get = AsyncMock(side_effect=[mock_pr, mock_repo])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    assert len(result) == len(sample_llm_output.learning_items)
    assert mock_pr.processed is True
    assert result[0].workspace_id == 456
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_learning_items_sets_schema_version(sample_llm_output):
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock(repository_id=123, processed=False)
    mock_repo = MagicMock(workspace_id=456)
    mock_db.get = AsyncMock(side_effect=[mock_pr, mock_repo])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_items = []
    mock_db.add = lambda item: added_items.append(item)

    await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    assert added_items[0].schema_version == "1.0"


@pytest.mark.asyncio
async def test_save_learning_items_returns_list(sample_llm_output):
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock(repository_id=123, processed=False)
    mock_repo = MagicMock(workspace_id=456)
    mock_db.get = AsyncMock(side_effect=[mock_pr, mock_repo])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_save_learning_items_marks_pr_processed(sample_llm_output):
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock(repository_id=123, processed=False)
    mock_repo = MagicMock(workspace_id=456)
    mock_db.get = AsyncMock(side_effect=[mock_pr, mock_repo])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    await save_learning_items(sample_llm_output, pull_request_id=99, db=mock_db)

    assert mock_pr.processed is True
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_learning_items_pr_not_found_no_error(sample_llm_output):
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await save_learning_items(sample_llm_output, pull_request_id=999, db=mock_db)

    assert result == []
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_save_learning_items_item_fields(sample_llm_output):
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock(repository_id=123, processed=False)
    mock_repo = MagicMock(workspace_id=456)
    mock_db.get = AsyncMock(side_effect=[mock_pr, mock_repo])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_items = []
    mock_db.add = lambda item: added_items.append(item)

    await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    item = added_items[0]
    llm_item = sample_llm_output.learning_items[0]
    assert item.title == llm_item.title
    assert item.detail == llm_item.detail
    assert item.category == llm_item.category
    assert item.confidence == llm_item.confidence
    assert item.action_for_next_time == llm_item.action_for_next_time
    assert item.evidence == llm_item.evidence
    assert item.pull_request_id == 1
