import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_weekly_digest_no_items():
    from app.services.digest_generator import generate_weekly_digest

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_provider = MagicMock()

    digest = await generate_weekly_digest(2026, 1, 1, mock_provider, mock_db)

    assert digest.pr_count == 0
    assert digest.learning_count == 0
    mock_provider.generate_text.assert_not_called()


@pytest.mark.asyncio
async def test_call_llm_for_digest_retries_on_failure(mock_llm_provider):
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
    from app.services.digest_generator import _call_llm_for_digest

    result = await _call_llm_for_digest("test prompt", mock_llm_provider)

    assert isinstance(result, dict)
    assert result["summary"] == "Weekly digest summary"


@pytest.mark.asyncio
async def test_call_llm_for_digest_fallback_after_all_retries_fail(mock_llm_provider):
    from app.services.digest_generator import _call_llm_for_digest

    mock_llm_provider.generate_text = AsyncMock(side_effect=ConnectionError("Always fails"))

    with patch("app.services.digest_generator.asyncio.sleep", new_callable=AsyncMock):
        result = await _call_llm_for_digest("fallback prompt text", mock_llm_provider)

    assert isinstance(result, dict)
    assert result["summary"].startswith("fallback prompt text")
    assert result["repeated_issues"] == []
    assert result["next_time_notes"] == []


@pytest.mark.asyncio
async def test_generate_weekly_digest_saves_to_db():
    from app.services.digest_generator import generate_weekly_digest

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    mock_db.scalar = AsyncMock(return_value=None)

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_provider = MagicMock()

    await generate_weekly_digest(2026, 5, 5, mock_provider, mock_db)

    mock_db.commit.assert_called_once()
    from app.db.models import WeeklyDigest

    assert any(isinstance(obj, WeeklyDigest) for obj in added_objects)
    assert added_objects[0].workspace_id == 5


@pytest.mark.asyncio
async def test_generate_weekly_digest_updates_existing():
    from app.services.digest_generator import generate_weekly_digest

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))

    existing_digest = MagicMock()
    existing_digest.summary = "old summary"
    mock_db.scalar = AsyncMock(return_value=existing_digest)

    added_objects = []
    mock_db.add = lambda obj: added_objects.append(obj)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_provider = MagicMock()

    digest = await generate_weekly_digest(2026, 5, 5, mock_provider, mock_db)

    assert added_objects == []
    assert existing_digest.summary != "old summary"
    assert digest is existing_digest
