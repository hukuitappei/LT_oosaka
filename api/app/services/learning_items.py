from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, PullRequest, Repository
from app.schemas.learning_items import (
    LearningItemsCategoryCount,
    LearningItemsSummaryResponse,
    LearningItemsWeeklyPoint,
    LearningItemResponse,
    PullRequestRef,
    RepositoryRef,
)


class LearningItemNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class LearningWeek:
    year: int
    week: int


def _week_sequence(*, today: date, weeks: int) -> list[LearningWeek]:
    current_monday = today - timedelta(days=today.weekday())
    sequence: list[LearningWeek] = []
    for offset in range(weeks - 1, -1, -1):
        target_day = current_monday - timedelta(weeks=offset)
        year, week, _ = target_day.isocalendar()
        sequence.append(LearningWeek(year=year, week=week))
    return sequence


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


async def summarize_workspace_learning_items(
    db: AsyncSession,
    workspace_id: int,
    *,
    weeks: int = 8,
    today: date | None = None,
) -> LearningItemsSummaryResponse:
    result = await db.execute(
        select(LearningItem.category, LearningItem.created_at)
        .where(LearningItem.workspace_id == workspace_id)
        .order_by(LearningItem.created_at.desc())
    )
    rows = result.all()

    today_value = today or date.today()
    week_sequence = _week_sequence(today=today_value, weeks=weeks)
    weekly_counts = {(point.year, point.week): 0 for point in week_sequence}
    category_counts: Counter[str] = Counter()

    for category, created_at in rows:
        category_counts[category] += 1
        created_date = created_at.date()
        year, week, _ = created_date.isocalendar()
        key = (year, week)
        if key in weekly_counts:
            weekly_counts[key] += 1

    current_year, current_week, _ = today_value.isocalendar()
    return LearningItemsSummaryResponse(
        total_learning_items=len(rows),
        current_week_count=weekly_counts.get((current_year, current_week), 0),
        weekly_points=[
            LearningItemsWeeklyPoint(
                year=point.year,
                week=point.week,
                label=f"{point.year}-W{point.week:02d}",
                learning_count=weekly_counts[(point.year, point.week)],
            )
            for point in week_sequence
        ],
        top_categories=[
            LearningItemsCategoryCount(category=category, count=count)
            for category, count in category_counts.most_common(5)
        ],
    )
