from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.schemas.llm_output import LLMOutputV1
from app.services.extractor import extract_from_pr, load_fixture
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.ollama_provider import OllamaProvider
from app.config import settings

router = APIRouter(prefix="/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    pr_id: str
    provider: str = "anthropic"  # "anthropic" or "ollama"


@router.post("/pr", response_model=LLMOutputV1)
async def analyze_pr(request: AnalyzeRequest):
    """サンプルPRから学びを抽出する"""
    try:
        pr_data = load_fixture(request.pr_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"PR fixture '{request.pr_id}' not found")

    if request.provider == "anthropic":
        if not settings.anthropic_api_key:
            raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")
        provider = AnthropicProvider(api_key=settings.anthropic_api_key)
    elif request.provider == "ollama":
        provider = OllamaProvider(host=settings.ollama_base_url)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")

    try:
        result = await extract_from_pr(pr_data, provider)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fixtures")
async def list_fixtures() -> list[str]:
    """利用可能なサンプルPR一覧を返す"""
    from pathlib import Path
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    return [p.stem for p in fixtures_dir.glob("*.json")]
