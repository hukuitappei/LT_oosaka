from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Repository, SpaceSettings, Workspace


@dataclass
class SpaceSettingsView:
    workspace_id: int
    display_name: str
    description: str | None
    default_visibility: str
    active_goal: str | None
    active_focus_labels: list[str]
    primary_repository_ids: list[int]


class SpaceSettingsValidationError(Exception):
    pass


def _view_from_workspace(workspace: Workspace, settings: SpaceSettings | None) -> SpaceSettingsView:
    if settings is None:
        return SpaceSettingsView(
            workspace_id=workspace.id,
            display_name=workspace.name,
            description=None,
            default_visibility="workspace_shared",
            active_goal=None,
            active_focus_labels=[],
            primary_repository_ids=[],
        )

    return SpaceSettingsView(
        workspace_id=workspace.id,
        display_name=settings.display_name or workspace.name,
        description=settings.description,
        default_visibility=settings.default_visibility,
        active_goal=settings.active_goal,
        active_focus_labels=list(settings.active_focus_labels or []),
        primary_repository_ids=list(settings.primary_repository_ids or []),
    )


async def get_space_settings_view(db: AsyncSession, workspace: Workspace) -> SpaceSettingsView:
    settings = await db.scalar(select(SpaceSettings).where(SpaceSettings.workspace_id == workspace.id))
    return _view_from_workspace(workspace, settings)


async def update_space_settings(
    db: AsyncSession,
    workspace: Workspace,
    *,
    display_name: str | None = None,
    description: str | None = None,
    default_visibility: str | None = None,
    active_goal: str | None = None,
    active_focus_labels: list[str] | None = None,
    primary_repository_ids: list[int] | None = None,
) -> SpaceSettingsView:
    settings = await db.scalar(select(SpaceSettings).where(SpaceSettings.workspace_id == workspace.id))
    if settings is None:
        settings = SpaceSettings(workspace_id=workspace.id)
        db.add(settings)

    if primary_repository_ids is not None:
        if primary_repository_ids:
            repo_ids = list(
                (
                    await db.scalars(
                        select(Repository.id).where(
                            Repository.workspace_id == workspace.id,
                            Repository.id.in_(primary_repository_ids),
                        )
                    )
                ).all()
            )
            if len(repo_ids) != len(set(primary_repository_ids)):
                raise SpaceSettingsValidationError("Primary repositories must belong to the current space")
        settings.primary_repository_ids = list(primary_repository_ids)

    if active_focus_labels is not None:
        settings.active_focus_labels = list(active_focus_labels)
    if display_name is not None:
        settings.display_name = display_name or None
    if description is not None:
        settings.description = description or None
    if default_visibility is not None:
        settings.default_visibility = default_visibility
    if active_goal is not None:
        settings.active_goal = active_goal or None

    await db.commit()
    await db.refresh(settings)
    return _view_from_workspace(workspace, settings)
