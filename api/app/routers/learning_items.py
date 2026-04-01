from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role
from app.schemas.learning_items import (
    LearningItemsSummaryResponse,
    LearningItemResponse,
    LearningItemUpdateRequest,
)
from app.services.learning_items import (
    LearningItemNotFoundError,
    get_workspace_learning_item,
    list_workspace_learning_items,
    summarize_workspace_learning_items,
    update_workspace_learning_item,
)

router = APIRouter(prefix="/learning-items", tags=["learning-items"])


@router.get("/", response_model=list[LearningItemResponse])
async def list_learning_items(
    q: str | None = None,
    repository_id: int | None = None,
    pr_id: int | None = None,
    category: str | None = None,
    status: str | None = None,
    visibility: str | None = None,
    limit: int = 100,
    offset: int = 0,
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
        q=q,
        repository_id=repository_id,
        pr_id=pr_id,
        category=category,
        status=status,
        visibility=visibility,
        limit=max(1, min(limit, 200)),
        offset=max(0, offset),
    )


@router.get("/summary", response_model=LearningItemsSummaryResponse)
async def get_learning_items_summary(
    weeks: int = 8,
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
    return await summarize_workspace_learning_items(
        db,
        current_workspace.id,
        weeks=max(1, min(weeks, 26)),
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


@router.patch("/{item_id}", response_model=LearningItemResponse)
async def update_learning_item(
    item_id: int,
    request: LearningItemUpdateRequest,
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
    if request.status is None and request.visibility is None:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        return await update_workspace_learning_item(
            db,
            item_id,
            current_workspace.id,
            status=request.status,
            visibility=request.visibility,
        )
    except LearningItemNotFoundError:
        raise HTTPException(status_code=404, detail="Learning item not found")
