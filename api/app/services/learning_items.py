from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, PullRequest, Repository
from app.schemas.learning_items import LearningItemResponse, PullRequestRef, RepositoryRef


class LearningItemNotFoundError(Exception):
    pass


def _learning_items_query(workspace_id: int):
    return (
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(LearningItem.pull_request).selectinload(PullRequest.repository)
        )
        .where(LearningItem.workspace_id == workspace_id)
    )


def to_learning_item_response(item: LearningItem) -> LearningItemResponse:
    pull_request = item.pull_request
    repository = pull_request.repository
    return LearningItemResponse(
        id=item.id,
        pull_request_id=item.pull_request_id,
        title=item.title,
        detail=item.detail,
        category=item.category,
        confidence=item.confidence,
        action_for_next_time=item.action_for_next_time,
        evidence=item.evidence,
        visibility=item.visibility,
        created_at=item.created_at,
        repository=RepositoryRef.model_validate(repository),
        pull_request=PullRequestRef.model_validate(pull_request),
    )


async def list_workspace_learning_items(
    db: AsyncSession,
    workspace_id: int,
    *,
    category: str | None = None,
    visibility: str | None = None,
) -> list[LearningItemResponse]:
    stmt = _learning_items_query(workspace_id).order_by(LearningItem.created_at.desc())
    if category:
        stmt = stmt.where(LearningItem.category == category)
    if visibility:
        stmt = stmt.where(LearningItem.visibility == visibility)
    result = await db.execute(stmt)
    return [to_learning_item_response(item) for item in result.scalars().all()]


async def get_workspace_learning_item(
    db: AsyncSession,
    item_id: int,
    workspace_id: int,
) -> LearningItemResponse:
    item = await db.scalar(
        _learning_items_query(workspace_id).where(LearningItem.id == item_id)
    )
    if not item:
        raise LearningItemNotFoundError
    return to_learning_item_response(item)
