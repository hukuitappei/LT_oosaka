from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.db.models import LearningItem, PullRequest, Repository, User
from app.dependencies import get_current_user

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
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[LearningItemResponse])
async def list_learning_items(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .where(Repository.user_id == current_user.id)
        .order_by(LearningItem.created_at.desc())
    )
    if category:
        stmt = stmt.where(LearningItem.category == category)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=LearningItemResponse)
async def get_learning_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await db.get(LearningItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Learning item not found")
    return item
