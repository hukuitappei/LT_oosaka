from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GitHubConnection, LearningItem, PullRequest, Repository, ReviewComment, User, WeeklyDigest, Workspace, WorkspaceMember


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceUserNotFoundError(Exception):
    pass


class WorkspaceMemberAlreadyExistsError(Exception):
    pass


class WorkspaceMemberNotFoundError(Exception):
    pass


class WorkspacePermissionError(Exception):
    pass


class WorkspaceDeleteConfirmationError(Exception):
    pass


class WorkspaceDeletePermissionError(Exception):
    pass


@dataclass(frozen=True)
class WorkspacePurgeResult:
    workspace_id: int
    deleted_learning_items: int
    deleted_review_comments: int
    deleted_pull_requests: int
    deleted_repositories: int
    deleted_weekly_digests: int
    deleted_github_connections: int
    deleted_memberships: int


@dataclass(frozen=True)
class WorkspaceSummary:
    id: int
    name: str
    slug: str
    is_personal: bool
    role: str
    created_at: datetime


def build_workspace_summary(workspace: Workspace, role: str) -> WorkspaceSummary:
    return WorkspaceSummary(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        is_personal=workspace.is_personal,
        role=role,
        created_at=workspace.created_at,
    )


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


async def create_workspace_for_user(
    db: AsyncSession,
    *,
    name: str,
    owner: User,
) -> WorkspaceSummary:
    workspace = await create_workspace(db, name=name, owner=owner)
    await db.commit()
    await db.refresh(workspace)
    return build_workspace_summary(workspace, "owner")


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


async def get_current_workspace_summary(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
) -> WorkspaceSummary:
    return await get_user_workspace_summary(db, workspace_id, user_id)


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


async def list_user_workspace_summaries(
    db: AsyncSession,
    user_id: int,
) -> list[WorkspaceSummary]:
    return [
        build_workspace_summary(workspace, role)
        for workspace, role in await list_user_workspaces(db, user_id)
    ]


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


async def get_user_workspace_summary(
    db: AsyncSession,
    workspace_id: int,
    user_id: int,
) -> WorkspaceSummary:
    workspace, role = await get_user_workspace(db, workspace_id, user_id)
    return build_workspace_summary(workspace, role)


async def get_workspace_by_id(
    db: AsyncSession,
    workspace_id: int,
) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError
    return workspace


async def require_workspace_admin_membership(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
) -> Workspace:
    workspace = await get_workspace_by_id(db, workspace_id)
    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if member is None:
        raise WorkspaceNotFoundError
    if member.role not in {"owner", "admin"}:
        raise WorkspacePermissionError
    return workspace


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


async def add_workspace_member_to_workspace(
    db: AsyncSession,
    *,
    workspace_id: int,
    actor_user_id: int,
    email: str,
    role: str,
) -> None:
    await require_workspace_admin_membership(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
    )
    await add_workspace_member_by_email(db, workspace_id, email, role)


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


async def update_workspace_member_role_in_workspace(
    db: AsyncSession,
    *,
    workspace_id: int,
    actor_user_id: int,
    target_user_id: int,
    role: str,
) -> None:
    await require_workspace_admin_membership(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
    )
    await update_workspace_member_role(db, workspace_id, target_user_id, role)


async def purge_workspace(
    db: AsyncSession,
    *,
    workspace_id: int,
    actor_user_id: int,
    confirm_slug: str,
) -> WorkspacePurgeResult:
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace.slug != confirm_slug:
        raise WorkspaceDeleteConfirmationError

    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == actor_user_id,
        )
    )
    if member is None:
        raise WorkspaceNotFoundError
    if member.role != "owner":
        raise WorkspaceDeletePermissionError

    pr_ids = select(PullRequest.id).join(Repository, PullRequest.repository_id == Repository.id).where(
        Repository.workspace_id == workspace_id
    )
    repository_ids = select(Repository.id).where(Repository.workspace_id == workspace_id)

    deleted_learning_items = (
        await db.execute(delete(LearningItem).where(LearningItem.workspace_id == workspace_id))
    ).rowcount or 0
    deleted_review_comments = (
        await db.execute(delete(ReviewComment).where(ReviewComment.pull_request_id.in_(pr_ids)))
    ).rowcount or 0
    deleted_pull_requests = (
        await db.execute(delete(PullRequest).where(PullRequest.id.in_(pr_ids)))
    ).rowcount or 0
    deleted_repositories = (
        await db.execute(delete(Repository).where(Repository.id.in_(repository_ids)))
    ).rowcount or 0
    deleted_weekly_digests = (
        await db.execute(delete(WeeklyDigest).where(WeeklyDigest.workspace_id == workspace_id))
    ).rowcount or 0
    deleted_github_connections = (
        await db.execute(delete(GitHubConnection).where(GitHubConnection.workspace_id == workspace_id))
    ).rowcount or 0
    deleted_memberships = (
        await db.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id))
    ).rowcount or 0
    await db.execute(delete(Workspace).where(Workspace.id == workspace_id))
    await db.commit()
    return WorkspacePurgeResult(
        workspace_id=workspace_id,
        deleted_learning_items=deleted_learning_items,
        deleted_review_comments=deleted_review_comments,
        deleted_pull_requests=deleted_pull_requests,
        deleted_repositories=deleted_repositories,
        deleted_weekly_digests=deleted_weekly_digests,
        deleted_github_connections=deleted_github_connections,
        deleted_memberships=deleted_memberships,
    )
