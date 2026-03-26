from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.llm_output import LLMOutputV1
from app.services.extractor import extract_from_pr, load_fixture
from app.services.learning_saver import save_learning_items
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.ollama_provider import OllamaProvider
from app.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    pr_id: str
    provider: str = "anthropic"
    pull_request_id: int | None = None  # 指定時はDBに保存


@router.post("/pr", response_model=LLMOutputV1)
async def analyze_pr(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """サンプルPRから学びを抽出する。pull_request_id を指定するとDBに保存される。"""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if request.pull_request_id is not None:
        await save_learning_items(result, request.pull_request_id, db)

    return result


@router.get("/fixtures")
async def list_fixtures() -> list[str]:
    """利用可能なサンプルPR一覧を返す"""
    from pathlib import Path
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    return [p.stem for p in fixtures_dir.glob("*.json")]
