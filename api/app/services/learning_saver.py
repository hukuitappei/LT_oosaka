from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import LearningItem as LearningItemModel, PullRequest
from app.schemas.llm_output import LLMOutputV1


async def save_learning_items(
    output: LLMOutputV1,
    pull_request_id: int,
    db: AsyncSession,
) -> list[LearningItemModel]:
    """LLMOutputV1 の learning_items を DB に保存する"""
    items = []
    for item in output.learning_items:
        db_item = LearningItemModel(
            pull_request_id=pull_request_id,
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

    # PullRequest を処理済みにマーク
    pr = await db.get(PullRequest, pull_request_id)
    if pr:
        pr.processed = True

    await db.commit()
    for item in items:
        await db.refresh(item)
    return items
