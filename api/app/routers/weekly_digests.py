from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, get_current_workspace_member
from app.services.weekly_digests import (
    WeeklyDigestNotFoundError,
    WeeklyDigestProviderUnavailableError,
    generate_workspace_weekly_digest,
    get_workspace_weekly_digest,
    list_workspace_weekly_digests,
    resolve_weekly_digest_period,
)

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
    reuse_event_count: int
    reused_learning_item_count: int
    recurring_reuse_event_count: int
    clean_reuse_event_count: int
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
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return await list_workspace_weekly_digests(db, current_workspace.id)


@router.get("/{digest_id}", response_model=WeeklyDigestResponse)
async def get_weekly_digest(
    digest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return await get_workspace_weekly_digest(db, digest_id, current_workspace.id)
    except WeeklyDigestNotFoundError:
        raise HTTPException(status_code=404, detail="Weekly digest not found")


@router.post("/generate", response_model=WeeklyDigestResponse)
async def generate_digest(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    period = resolve_weekly_digest_period(request.year, request.week)

    try:
        return await generate_workspace_weekly_digest(
            db,
            current_workspace.id,
            year=period.year,
            week=period.week,
        )
    except WeeklyDigestProviderUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
