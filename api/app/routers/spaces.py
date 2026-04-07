from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role
from app.services.space_settings import (
    SpaceSettingsValidationError,
    get_space_settings_view,
    update_space_settings,
)
from app.services.workspaces import (
    WorkspaceNotFoundError,
    create_workspace,
    get_user_workspace,
    list_user_workspaces,
)

router = APIRouter(prefix="/spaces", tags=["spaces"])


class SpaceOut(BaseModel):
    id: int
    name: str
    slug: str
    is_personal: bool
    role: str
    created_at: datetime


class CreateSpaceRequest(BaseModel):
    name: str


class SpaceSettingsOut(BaseModel):
    workspace_id: int
    display_name: str
    description: str | None
    default_visibility: str
    active_goal: str | None
    active_focus_labels: list[str]
    primary_repository_ids: list[int]


class UpdateSpaceSettingsRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    default_visibility: str | None = None
    active_goal: str | None = None
    active_focus_labels: list[str] | None = None
    primary_repository_ids: list[int] | None = None


def _space_out(workspace: Workspace, role: str) -> SpaceOut:
    return SpaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        is_personal=workspace.is_personal,
        role=role,
        created_at=workspace.created_at,
    )


@router.get("/", response_model=list[SpaceOut])
async def list_spaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await list_user_workspaces(db, current_user.id)
    return [_space_out(workspace, role) for workspace, role in result]


@router.post("/", response_model=SpaceOut, status_code=status.HTTP_201_CREATED)
async def create_space(
    request: CreateSpaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await create_workspace(db, name=request.name, owner=current_user)
    await db.commit()
    await db.refresh(workspace)
    return _space_out(workspace, "owner")


@router.get("/{space_id}", response_model=SpaceOut)
async def get_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        workspace, role = await get_user_workspace(db, space_id, current_user.id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Space not found")
    return _space_out(workspace, role)


@router.get("/current/context", response_model=SpaceOut)
async def get_current_space_context(
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    return _space_out(workspace, member.role)


@router.get("/{space_id}/settings", response_model=SpaceSettingsOut)
async def get_space_settings(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        workspace, _ = await get_user_workspace(db, space_id, current_user.id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Space not found")
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    return SpaceSettingsOut(**(await get_space_settings_view(db, workspace)).__dict__)


@router.patch("/{space_id}/settings", response_model=SpaceSettingsOut)
async def patch_space_settings(
    space_id: int,
    request: UpdateSpaceSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        workspace, _ = await get_user_workspace(db, space_id, current_user.id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Space not found")
    await require_workspace_role(
        {"owner", "admin"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    try:
        view = await update_space_settings(
            db,
            workspace,
            display_name=request.display_name,
            description=request.description,
            default_visibility=request.default_visibility,
            active_goal=request.active_goal,
            active_focus_labels=request.active_focus_labels,
            primary_repository_ids=request.primary_repository_ids,
        )
    except SpaceSettingsValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SpaceSettingsOut(**view.__dict__)
