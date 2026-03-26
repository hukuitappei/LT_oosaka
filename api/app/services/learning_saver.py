from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningItem as LearningItemModel, PullRequest, Repository
from app.schemas.llm_output import LLMOutputV1


async def save_learning_items(
    output: LLMOutputV1,
    pull_request_id: int,
    db: AsyncSession,
    *,
    created_by_user_id: int | None = None,
    visibility: str = "private_draft",
) -> list[LearningItemModel]:
    """LLMOutputV1 の learning_items を DB に保存する"""
    pr = await db.get(PullRequest, pull_request_id)
    if pr is None:
        return []

    repository = await db.get(Repository, pr.repository_id)
    if repository is None:
        return []

    items = []
    for item in output.learning_items:
        db_item = LearningItemModel(
            workspace_id=repository.workspace_id,
            pull_request_id=pull_request_id,
            created_by_user_id=created_by_user_id,
            visibility=visibility,
            schema_version=output.schema_version,
            title=item.title,
            detail=item.detail,
            category=item.category,
            confidence=item.confidence,
            action_for_next_time=item.action_for_next_time,
            evidence=item.evidence,
        )
        db.add(db_item)
        items.append(db_item)

    pr.processed = True

    await db.commit()
    for item in items:
        await db.refresh(item)
    return items
