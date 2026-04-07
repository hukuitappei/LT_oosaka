from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PullRequest, Repository
from app.schemas.handoffs import ReanalysisRequest

logger = logging.getLogger(__name__)


class PullRequestNotFoundError(Exception):
    pass


async def get_workspace_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
) -> PullRequest | None:
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(selectinload(PullRequest.learning_items))
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


async def request_reanalysis_for_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
    user_id: int,
) -> dict[str, int | str]:
    pr = await get_workspace_pull_request(db, pr_id, workspace_id)
    if not pr:
        raise PullRequestNotFoundError

    from app.tasks.extract import reanalyze_pr_task

    request = ReanalysisRequest(pr_id=pr.id, workspace_id=workspace_id, user_id=user_id)
    reanalyze_pr_task.delay(request.model_dump(mode="python"))
    logger.info(
        "request_reanalysis_for_pull_request enqueued pr_id=%d workspace_id=%d user_id=%d",
        pr.id,
        workspace_id,
        user_id,
    )
    return {"status": "accepted", "pr_id": pr_id}
