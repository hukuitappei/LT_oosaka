from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.llm import get_llm_provider
from app.schemas.llm_output import LLMOutputV1
from app.services.extractor import extract_from_pr, load_fixture
from app.services.learning_saver import save_learning_items

router = APIRouter(prefix="/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    pr_id: str
    provider: str = "anthropic"
    pull_request_id: int | None = None


@router.post("/pr", response_model=LLMOutputV1)
async def analyze_pr(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Analyze a fixture-backed PR sample and optionally persist learning items."""
    try:
        pr_data = load_fixture(request.pr_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"PR fixture '{request.pr_id}' not found")

    try:
        provider = get_llm_provider(request.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await extract_from_pr(pr_data, provider)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if request.pull_request_id is not None:
        await save_learning_items(result, request.pull_request_id, db)

    return result


@router.get("/fixtures")
async def list_fixtures() -> list[str]:
    """List available fixture PR samples."""
    from pathlib import Path

    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    return [p.stem for p in fixtures_dir.glob("*.json")]
