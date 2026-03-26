from datetime import date
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.db.models import WeeklyDigest, User
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/weekly-digests", tags=["weekly-digests"])


class WeeklyDigestResponse(BaseModel):
    id: int
    year: int
    week: int
    summary: str
    repeated_issues: list[str]
    next_time_notes: list[str]
    pr_count: int
    learning_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    year: int | None = None
    week: int | None = None


@router.get("/", response_model=list[WeeklyDigestResponse])
async def list_weekly_digests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WeeklyDigest).order_by(WeeklyDigest.year.desc(), WeeklyDigest.week.desc())
    )
    return result.scalars().all()


@router.get("/{digest_id}", response_model=WeeklyDigestResponse)
async def get_weekly_digest(
    digest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    digest = await db.get(WeeklyDigest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Weekly digest not found")
    return digest


@router.post("/generate", response_model=WeeklyDigestResponse)
async def generate_digest(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """指定週（省略時は今週）の週報を生成する"""
    today = date.today()
    year = request.year or today.isocalendar()[0]
    week = request.week or today.isocalendar()[1]

    if settings.anthropic_api_key:
        from app.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key=settings.anthropic_api_key)
    elif settings.ollama_base_url:
        from app.llm.ollama_provider import OllamaProvider
        provider = OllamaProvider(host=settings.ollama_base_url)
    else:
        raise HTTPException(status_code=400, detail="No LLM provider configured")

    from app.services.digest_generator import generate_weekly_digest
    return await generate_weekly_digest(year, week, provider, db)
