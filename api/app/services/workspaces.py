from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember


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
