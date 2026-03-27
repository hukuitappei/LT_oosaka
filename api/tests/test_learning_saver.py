import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_save_learning_items_creates_records(sample_llm_output):
    """save_learning_items が LearningItem レコードを作成し PR を処理済みにする"""
    from app.services.learning_saver import save_learning_items

    # Mock DB session
    mock_db = AsyncMock()
    mock_pr = MagicMock()
    mock_pr.processed = False
    mock_db.get = AsyncMock(return_value=mock_pr)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    assert len(result) == len(sample_llm_output.learning_items)
    assert mock_pr.processed is True
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_learning_items_sets_schema_version(sample_llm_output):
    """保存された LearningItem に schema_version が正しくセットされる"""
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_pr)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added_items = []
    mock_db.add = lambda item: added_items.append(item)

    await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    # Check schema version on first item
    assert added_items[0].schema_version == "1.0"


@pytest.mark.asyncio
async def test_save_learning_items_returns_list(sample_llm_output):
    """save_learning_items は LearningItem のリストを返す"""
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_pr)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await save_learning_items(sample_llm_output, pull_request_id=1, db=mock_db)

    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_save_learning_items_marks_pr_processed(sample_llm_output):
    """PR が存在する場合は processed=True にマークされる"""
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock()
    mock_pr.processed = False
    mock_db.get = AsyncMock(return_value=mock_pr)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    await save_learning_items(sample_llm_output, pull_request_id=99, db=mock_db)

    # Verify db.get was called with correct PR id
    mock_db.get.assert_called_once()
    call_args = mock_db.get.call_args
    # Second arg should be the pull_request_id
    assert call_args[0][1] == 99
    assert mock_pr.processed is True


@pytest.mark.asyncio
async def test_save_learning_items_pr_not_found_no_error(sample_llm_output):
    """PR が DB に存在しない場合でもエラーにならない"""
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Should not raise even when PR not found
    result = await save_learning_items(sample_llm_output, pull_request_id=999, db=mock_db)
    assert isinstance(result, list)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_learning_items_item_fields(sample_llm_output):
    """保存される LearningItem の各フィールドが正しくセットされる"""
    from app.services.learning_saver import save_learning_items

    mock_db = AsyncMock()
    mock_pr = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_pr)
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
