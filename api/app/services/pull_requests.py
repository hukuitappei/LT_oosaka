from __future__ import annotations

import logging
from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, LearningReuseEvent, PullRequest, Repository
from app.schemas.handoffs import ReanalysisRequest
from app.services.related_learning_recommendations import (
    RelatedLearningItemMatch,
    recommend_related_learning_items,
)

logger = logging.getLogger(__name__)


class PullRequestNotFoundError(Exception):
    pass


class RelatedLearningItemNotFoundError(Exception):
    pass


async def get_workspace_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
) -> PullRequest | None:
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(PullRequest.learning_items),
            selectinload(PullRequest.repository),
            selectinload(PullRequest.review_comments),
        )
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


async def get_related_learning_items_for_pull_request(
    db: AsyncSession,
    pr: PullRequest,
    workspace_id: int,
) -> list[RelatedLearningItemMatch]:
    result = await db.execute(
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(LearningItem.pull_request).selectinload(PullRequest.repository),
            selectinload(LearningItem.pull_request).selectinload(PullRequest.learning_items),
            selectinload(LearningItem.pull_request).selectinload(PullRequest.review_comments),
        )
        .where(
            LearningItem.workspace_id == workspace_id,
            LearningItem.pull_request_id != pr.id,
        )
        .order_by(LearningItem.created_at.desc())
    )
    matches = recommend_related_learning_items(pr, list(result.scalars().all()))
    if not matches:
        return []

    item_ids = [match.item.id for match in matches]
    reuse_counts_result = await db.execute(
        select(
            LearningReuseEvent.source_learning_item_id,
            func.count(LearningReuseEvent.id),
        )
        .where(
            LearningReuseEvent.workspace_id == workspace_id,
            LearningReuseEvent.source_learning_item_id.in_(item_ids),
        )
        .group_by(LearningReuseEvent.source_learning_item_id)
    )
    reuse_counts = {item_id: count for item_id, count in reuse_counts_result.all()}

    current_pr_result = await db.execute(
        select(LearningReuseEvent.source_learning_item_id).where(
            LearningReuseEvent.workspace_id == workspace_id,
            LearningReuseEvent.target_pull_request_id == pr.id,
            LearningReuseEvent.source_learning_item_id.in_(item_ids),
        )
    )
    reused_in_current_pr = set(current_pr_result.scalars().all())

    return [
        replace(
            match,
            reuse_count=reuse_counts.get(match.item.id, 0),
            reused_in_current_pr=match.item.id in reused_in_current_pr,
        )
        for match in matches
    ]


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


async def record_learning_reuse_for_pull_request(
    db: AsyncSession,
    *,
    source_learning_item_id: int,
    target_pr_id: int,
    workspace_id: int,
    user_id: int,
) -> dict[str, int | bool]:
    target_pr = await get_workspace_pull_request(db, target_pr_id, workspace_id)
    if not target_pr:
        raise PullRequestNotFoundError

    source_item = await db.scalar(
        select(LearningItem).where(
            LearningItem.id == source_learning_item_id,
            LearningItem.workspace_id == workspace_id,
        )
    )
    if not source_item:
        raise RelatedLearningItemNotFoundError
    if source_item.pull_request_id == target_pr_id:
        raise RelatedLearningItemNotFoundError

    existing = await db.scalar(
        select(LearningReuseEvent).where(
            LearningReuseEvent.workspace_id == workspace_id,
            LearningReuseEvent.source_learning_item_id == source_learning_item_id,
            LearningReuseEvent.target_pull_request_id == target_pr_id,
        )
    )
    if existing:
        return {
            "source_learning_item_id": source_learning_item_id,
            "target_pull_request_id": target_pr_id,
            "reuse_count": await _count_learning_reuse_events(db, workspace_id, source_learning_item_id),
            "already_recorded": True,
        }

    db.add(
        LearningReuseEvent(
            workspace_id=workspace_id,
            source_learning_item_id=source_learning_item_id,
            target_pull_request_id=target_pr_id,
            created_by_user_id=user_id,
        )
    )
    await db.commit()
    return {
        "source_learning_item_id": source_learning_item_id,
        "target_pull_request_id": target_pr_id,
        "reuse_count": await _count_learning_reuse_events(db, workspace_id, source_learning_item_id),
        "already_recorded": False,
    }


async def _count_learning_reuse_events(
    db: AsyncSession,
    workspace_id: int,
    source_learning_item_id: int,
) -> int:
    return int(
        await db.scalar(
            select(func.count(LearningReuseEvent.id)).where(
                LearningReuseEvent.workspace_id == workspace_id,
                LearningReuseEvent.source_learning_item_id == source_learning_item_id,
            )
        )
        or 0
    )
