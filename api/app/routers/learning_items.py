from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role
from app.schemas.learning_items import LearningItemResponse
from app.services.learning_items import (
    LearningItemNotFoundError,
    get_workspace_learning_item,
    list_workspace_learning_items,
)

router = APIRouter(prefix="/learning-items", tags=["learning-items"])


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
    return await list_workspace_learning_items(
        db,
        current_workspace.id,
        category=category,
        visibility=visibility,
    )


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
    try:
        return await get_workspace_learning_item(db, item_id, current_workspace.id)
    except LearningItemNotFoundError:
        raise HTTPException(status_code=404, detail="Learning item not found")
