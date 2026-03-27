from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PullRequest, Repository


class RepositoryNotFoundError(Exception):
    pass


async def list_workspace_repositories(
    db: AsyncSession,
    workspace_id: int,
) -> list[Repository]:
    result = await db.execute(
        select(Repository)
        .where(Repository.workspace_id == workspace_id)
        .order_by(Repository.created_at.desc())
    )
    return list(result.scalars().all())


async def list_workspace_repository_pull_requests(
    db: AsyncSession,
    repo_id: int,
    workspace_id: int,
) -> list[PullRequest]:
    repo = await db.scalar(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.workspace_id == workspace_id,
        )
    )
    if repo is None:
        raise RepositoryNotFoundError

    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.repository_id == repo_id)
        .order_by(PullRequest.created_at.desc())
    )
    return list(result.scalars().all())
