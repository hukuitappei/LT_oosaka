from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceUserNotFoundError(Exception):
    pass


class WorkspaceMemberAlreadyExistsError(Exception):
    pass


class WorkspaceMemberNotFoundError(Exception):
    pass


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return base or "workspace"


async def generate_workspace_slug(
    db: AsyncSession,
    name: str,
    *,
    suffix_seed: str | None = None,
) -> str:
    base = _slugify(suffix_seed or name)
    slug = base
    attempt = 2
    while await db.scalar(select(Workspace).where(Workspace.slug == slug)):
        slug = f"{base}-{attempt}"
        attempt += 1
    return slug


async def create_workspace(
    db: AsyncSession,
    *,
    name: str,
    owner: User,
    is_personal: bool = False,
) -> Workspace:
    workspace = Workspace(
        name=name,
        slug=await generate_workspace_slug(
            db,
            name,
            suffix_seed=owner.email.split("@")[0] if is_personal else None,
        ),
        is_personal=is_personal,
    )
    db.add(workspace)
    await db.flush()

    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner.id,
            role="owner",
        )
    )
    await db.flush()
    return workspace


async def ensure_personal_workspace(db: AsyncSession, user: User) -> Workspace:
    stmt = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.user_id == user.id,
            Workspace.is_personal.is_(True),
        )
        .limit(1)
    )
    workspace = await db.scalar(stmt)
    if workspace:
        return workspace

    name = f"{user.email.split('@')[0]}'s workspace"
    return await create_workspace(db, name=name, owner=user, is_personal=True)


def workspace_with_role_query(user_id: int):
    return (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.is_personal.desc(), Workspace.name.asc())
    )


async def list_user_workspaces(
    db: AsyncSession,
    user_id: int,
) -> list[tuple[Workspace, str]]:
    result = await db.execute(workspace_with_role_query(user_id))
    return [(workspace, role) for workspace, role in result.all()]


async def get_user_workspace(
    db: AsyncSession,
    workspace_id: int,
    user_id: int,
) -> tuple[Workspace, str]:
    row = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(Workspace.id == workspace_id, WorkspaceMember.user_id == user_id)
    )
    result = row.first()
    if result is None:
        raise WorkspaceNotFoundError
    return result


async def add_workspace_member_by_email(
    db: AsyncSession,
    workspace_id: int,
    email: str,
    role: str,
) -> None:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError

    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise WorkspaceUserNotFoundError

    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if existing:
        raise WorkspaceMemberAlreadyExistsError

    db.add(
        WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role,
        )
    )
    await db.commit()


async def update_workspace_member_role(
    db: AsyncSession,
    workspace_id: int,
    user_id: int,
    role: str,
) -> None:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError

    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if member is None:
        raise WorkspaceMemberNotFoundError

    member.role = role
    await db.commit()
