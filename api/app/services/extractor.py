import json
from pathlib import Path
from typing import Any
from app.services.preprocessor import build_prompt
from app.schemas.llm_output import LLMOutputV1
from app.llm.base import BaseLLMProvider


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def load_fixture(pr_id: str) -> dict[str, Any]:
    """サンプルPRデータをファイルから読み込む"""
    path = FIXTURES_DIR / f"{pr_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {pr_id}")
    return json.loads(path.read_text(encoding="utf-8"))


async def extract_from_pr(pr_data: dict[str, Any], provider: BaseLLMProvider) -> LLMOutputV1:
    """PRデータから学びを抽出する"""
    prompt = build_prompt(pr_data)
    return await provider.extract_learnings(prompt)
