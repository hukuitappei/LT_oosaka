import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.extractor import extract_from_pr
from app.schemas.llm_output import LLMOutputV1


@pytest.mark.asyncio
async def test_extract_from_pr_success(sample_pr_data, mock_llm_provider, sample_llm_output):
    result = await extract_from_pr(sample_pr_data, mock_llm_provider)
    assert isinstance(result, LLMOutputV1)
    assert len(result.learning_items) == 1
    mock_llm_provider.extract_learnings.assert_called_once()


@pytest.mark.asyncio
async def test_extract_from_pr_retries_on_failure(sample_pr_data, sample_llm_output):
    """LLM が最初の2回失敗して3回目に成功する場合のリトライ確認"""
    from unittest.mock import MagicMock
    from app.llm.base import BaseLLMProvider

    provider = MagicMock(spec=BaseLLMProvider)
    call_count = 0

    async def flaky_extract(prompt):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Transient error")
        return sample_llm_output

    provider.extract_learnings = flaky_extract

    # Patch sleep to avoid actual waiting
    with patch("app.services.extractor.asyncio.sleep", new_callable=AsyncMock):
        result = await extract_from_pr(sample_pr_data, provider)

    assert isinstance(result, LLMOutputV1)
    assert call_count == 3


@pytest.mark.asyncio
async def test_extract_from_pr_raises_after_max_retries(sample_pr_data):
    """全リトライが失敗した場合は例外が伝播する"""
    from unittest.mock import MagicMock
    from app.llm.base import BaseLLMProvider

    provider = MagicMock(spec=BaseLLMProvider)
    provider.extract_learnings = AsyncMock(side_effect=ConnectionError("Persistent error"))

    with patch("app.services.extractor.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ConnectionError):
            await extract_from_pr(sample_pr_data, provider)


@pytest.mark.asyncio
async def test_extract_from_pr_calls_build_prompt(sample_pr_data, mock_llm_provider):
    """extract_from_pr が build_prompt を呼び出してプロンプトを LLM に渡す"""
    with patch("app.services.extractor.build_prompt", wraps=__import__("app.services.preprocessor", fromlist=["build_prompt"]).build_prompt) as mock_build:
        await extract_from_pr(sample_pr_data, mock_llm_provider)
        mock_build.assert_called_once_with(sample_pr_data)


@pytest.mark.asyncio
async def test_extract_from_pr_max_retry_count(sample_pr_data):
    """リトライは最大3回まで（_MAX_RETRIES=3）"""
    from unittest.mock import MagicMock
    from app.llm.base import BaseLLMProvider

    provider = MagicMock(spec=BaseLLMProvider)
    call_count = 0

    async def always_fail(prompt):
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Always fails")

    provider.extract_learnings = always_fail

    with patch("app.services.extractor.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ConnectionError):
            await extract_from_pr(sample_pr_data, provider)

    assert call_count == 3
