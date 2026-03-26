from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningItem, User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

router = APIRouter(prefix="/learning-items", tags=["learning-items"])


class LearningItemResponse(BaseModel):
    id: int
    pull_request_id: int
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    visibility: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[LearningItemResponse])
async def list_learning_items(
    category: str | None = None,
    visibility: str | None = None,
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
    stmt = (
        select(LearningItem)
        .where(LearningItem.workspace_id == current_workspace.id)
        .order_by(LearningItem.created_at.desc())
    )
    if category:
        stmt = stmt.where(LearningItem.category == category)
    if visibility:
        stmt = stmt.where(LearningItem.visibility == visibility)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=LearningItemResponse)
async def get_learning_item(
    item_id: int,
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
    item = await db.scalar(
        select(LearningItem).where(
            LearningItem.id == item_id,
            LearningItem.workspace_id == current_workspace.id,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Learning item not found")
    return item
