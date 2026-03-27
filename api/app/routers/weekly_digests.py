from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User, WeeklyDigest, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

router = APIRouter(prefix="/weekly-digests", tags=["weekly-digests"])


class WeeklyDigestResponse(BaseModel):
    id: int
    workspace_id: int
    year: int
    week: int
    summary: str
    repeated_issues: list[str]
    next_time_notes: list[str]
    pr_count: int
    learning_count: int
    visibility: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    year: int | None = None
    week: int | None = None


@router.get("/", response_model=list[WeeklyDigestResponse])
async def list_weekly_digests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
    result = await db.execute(
        select(WeeklyDigest)
        .where(WeeklyDigest.workspace_id == current_workspace.id)
        .order_by(WeeklyDigest.year.desc(), WeeklyDigest.week.desc())
    )
    return result.scalars().all()


@router.get("/{digest_id}", response_model=WeeklyDigestResponse)
async def get_weekly_digest(
    digest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
    digest = await db.scalar(
        select(WeeklyDigest).where(
            WeeklyDigest.id == digest_id,
            WeeklyDigest.workspace_id == current_workspace.id,
        )
    )
    if not digest:
        raise HTTPException(status_code=404, detail="Weekly digest not found")
    return digest


@router.post("/generate", response_model=WeeklyDigestResponse)
async def generate_digest(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
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

    return await generate_weekly_digest(
        year,
        week,
        current_workspace.id,
        provider,
        db,
        user_id=current_user.id,
    )
