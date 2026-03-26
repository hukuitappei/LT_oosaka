import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_weekly_digest_no_items():
    """学習アイテムがない週は空のダイジェストを生成する"""
    from app.services.digest_generator import generate_weekly_digest

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_provider = MagicMock()

    digest = await generate_weekly_digest(2026, 1, mock_provider, mock_db)

    assert "学び" in digest.summary or digest.pr_count == 0
    mock_provider.generate_text.assert_not_called()


@pytest.mark.asyncio
async def test_call_llm_for_digest_retries_on_failure(mock_llm_provider):
    """LLM失敗時にリトライする"""
    from app.services.digest_generator import _call_llm_for_digest
    import json

    call_count = 0

    async def flaky_generate(system_prompt, user_message):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Transient")
        return json.dumps({"summary": "OK", "repeated_issues": [], "next_time_notes": []})

    mock_llm_provider.generate_text = flaky_generate

    with patch("app.services.digest_generator.asyncio.sleep", new_callable=AsyncMock):
        result = await _call_llm_for_digest("test prompt", mock_llm_provider)

    assert result["summary"] == "OK"
    assert call_count == 2


@pytest.mark.asyncio
async def test_call_llm_for_digest_success(mock_llm_provider):
    """正常時は LLM から JSON を取得してパースした dict を返す"""
    from app.services.digest_generator import _call_llm_for_digest

    result = await _call_llm_for_digest("test prompt", mock_llm_provider)

    assert isinstance(result, dict)
    assert "summary" in result
    assert result["summary"] == "テスト週報"


@pytest.mark.asyncio
async def test_call_llm_for_digest_fallback_after_all_retries_fail(mock_llm_provider):
    """全リトライ失敗時はフォールバック結果（プロンプト先頭）を返す"""
    from app.services.digest_generator import _call_llm_for_digest

    mock_llm_provider.generate_text = AsyncMock(side_effect=ConnectionError("Always fails"))

    with patch("app.services.digest_generator.asyncio.sleep", new_callable=AsyncMock):
        result = await _call_llm_for_digest("fallback prompt text", mock_llm_provider)

    # digest_generator returns a fallback dict (not raises) after all retries
    assert isinstance(result, dict)
    assert "summary" in result
    # Summary contains beginning of the prompt (up to 200 chars)
    assert "fallback prompt text" in result["summary"]
    assert result["repeated_issues"] == []
    assert result["next_time_notes"] == []


@pytest.mark.asyncio
async def test_generate_weekly_digest_saves_to_db():
    """週報が DB に保存されることを確認する"""
    from app.services.digest_generator import generate_weekly_digest

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    mock_db.scalar = AsyncMock(return_value=None)

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_provider = MagicMock()

    await generate_weekly_digest(2026, 5, mock_provider, mock_db)

    mock_db.commit.assert_called_once()
    # A WeeklyDigest object should have been added
    from app.db.models import WeeklyDigest
    added_types = [type(obj).__name__ for obj in added_objects]
    assert "WeeklyDigest" in added_types


@pytest.mark.asyncio
async def test_generate_weekly_digest_updates_existing():
    """既存のダイジェストがある場合は更新する（新規追加しない）"""
    from app.services.digest_generator import generate_weekly_digest

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))

    # Existing digest returned by scalar
    existing_digest = MagicMock()
    existing_digest.summary = "old summary"
    mock_db.scalar = AsyncMock(return_value=existing_digest)

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_provider = MagicMock()

    digest = await generate_weekly_digest(2026, 5, mock_provider, mock_db)

    # Should update in-place, not add a new object
    from app.db.models import WeeklyDigest
    added_types = [type(obj).__name__ for obj in added_objects]
    assert "WeeklyDigest" not in added_types
    # The existing digest's summary should have been updated
    assert existing_digest.summary != "old summary"
