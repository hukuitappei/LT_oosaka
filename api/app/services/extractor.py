import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from app.services.preprocessor import build_prompt
from app.schemas.llm_output import LLMOutputV1
from app.llm.base import BaseLLMProvider


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds


def load_fixture(pr_id: str) -> dict[str, Any]:
    """サンプルPRデータをファイルから読み込む"""
    path = FIXTURES_DIR / f"{pr_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {pr_id}")
    return json.loads(path.read_text(encoding="utf-8"))


async def extract_from_pr(pr_data: dict[str, Any], provider: BaseLLMProvider) -> LLMOutputV1:
    """PRデータから学びを抽出する（最大3回リトライ）"""
    prompt = build_prompt(pr_data)
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await provider.extract_learnings(prompt)
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "LLM extraction attempt %d/%d failed, retrying in %.1fs: %s",
                    attempt, _MAX_RETRIES, delay, exc,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("LLM extraction failed after %d attempts", _MAX_RETRIES)
    raise last_exc  # type: ignore[misc]
