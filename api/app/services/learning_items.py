from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, LearningReuseEvent, PullRequest, Repository
from app.schemas.learning_items import (
    LearningItemsCategoryCount,
    LearningItemsReusePoint,
    LearningItemsStatusCount,
    LearningItemsSummaryResponse,
    LearningItemsWeeklyPoint,
    LearningItemResponse,
    PullRequestRef,
    RepositoryRef,
)
from app.services.reuse_impact_metrics import build_reuse_impact_summary


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
        status=item.status,
        visibility=item.visibility,
        created_at=item.created_at,
        repository=RepositoryRef.model_validate(repository),
        pull_request=PullRequestRef.model_validate(pull_request),
    )


async def list_workspace_learning_items(
    db: AsyncSession,
    workspace_id: int,
    *,
    q: str | None = None,
    repository_id: int | None = None,
    pr_id: int | None = None,
    category: str | None = None,
    status: str | None = None,
    visibility: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[LearningItemResponse]:
    stmt = _learning_items_query(workspace_id).order_by(LearningItem.created_at.desc())
    if q:
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(LearningItem.title).like(term),
                func.lower(LearningItem.detail).like(term),
                func.lower(LearningItem.evidence).like(term),
                func.lower(LearningItem.action_for_next_time).like(term),
                func.lower(PullRequest.title).like(term),
                func.lower(Repository.full_name).like(term),
            )
        )
    if repository_id is not None:
        stmt = stmt.where(Repository.id == repository_id)
    if pr_id is not None:
        stmt = stmt.where(PullRequest.id == pr_id)
    if category:
        stmt = stmt.where(LearningItem.category == category)
    if status:
        stmt = stmt.where(LearningItem.status == status)
    if visibility:
        stmt = stmt.where(LearningItem.visibility == visibility)
    stmt = stmt.limit(max(1, min(limit, 200))).offset(max(0, offset))
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


async def update_workspace_learning_item(
    db: AsyncSession,
    item_id: int,
    workspace_id: int,
    *,
    status: str | None = None,
    visibility: str | None = None,
) -> LearningItemResponse:
    item = await db.scalar(
        _learning_items_query(workspace_id).where(LearningItem.id == item_id)
    )
    if not item:
        raise LearningItemNotFoundError

    if status is not None:
        item.status = status
    if visibility is not None:
        item.visibility = visibility

    await db.commit()
    await db.refresh(item)
    return to_learning_item_response(item)


async def summarize_workspace_learning_items(
    db: AsyncSession,
    workspace_id: int,
    *,
    weeks: int = 8,
    today: date | None = None,
) -> LearningItemsSummaryResponse:
    learning_result = await db.execute(
        select(LearningItem.category, LearningItem.status, LearningItem.created_at)
        .where(LearningItem.workspace_id == workspace_id)
        .order_by(LearningItem.created_at.desc())
    )
    rows = learning_result.all()

    today_value = today or date.today()
    week_sequence = _week_sequence(today=today_value, weeks=weeks)
    weekly_counts = {(point.year, point.week): 0 for point in week_sequence}
    reuse_weekly_counts = {(point.year, point.week): 0 for point in week_sequence}
    category_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()

    for category, status, created_at in rows:
        category_counts[category] += 1
        status_counts[status] += 1
        created_date = created_at.date()
        year, week, _ = created_date.isocalendar()
        key = (year, week)
        if key in weekly_counts:
            weekly_counts[key] += 1

    reuse_result = await db.execute(
        select(LearningReuseEvent)
        .where(LearningReuseEvent.workspace_id == workspace_id)
        .options(
            selectinload(LearningReuseEvent.source_learning_item).selectinload(LearningItem.pull_request).selectinload(PullRequest.review_comments),
            selectinload(LearningReuseEvent.target_pull_request).selectinload(PullRequest.review_comments),
        )
        .order_by(LearningReuseEvent.created_at.desc())
    )
    reuse_events = list(reuse_result.scalars().all())
    reuse_summary = build_reuse_impact_summary(reuse_events)

    for event in reuse_events:
        created_date = event.created_at.date()
        year, week, _ = created_date.isocalendar()
        key = (year, week)
        if key in reuse_weekly_counts:
            reuse_weekly_counts[key] += 1

    current_year, current_week, _ = today_value.isocalendar()
    return LearningItemsSummaryResponse(
        total_learning_items=len(rows),
        current_week_count=weekly_counts.get((current_year, current_week), 0),
        total_reuse_events=reuse_summary.total_reuse_events,
        reused_learning_items_count=reuse_summary.reused_learning_items_count,
        current_week_reuse_count=reuse_weekly_counts.get((current_year, current_week), 0),
        recurring_reuse_events=reuse_summary.recurring_reuse_events,
        clean_reuse_events=reuse_summary.clean_reuse_events,
        weekly_points=[
            LearningItemsWeeklyPoint(
                year=point.year,
                week=point.week,
                label=f"{point.year}-W{point.week:02d}",
                learning_count=weekly_counts[(point.year, point.week)],
            )
            for point in week_sequence
        ],
        reuse_weekly_points=[
            LearningItemsReusePoint(
                year=point.year,
                week=point.week,
                label=f"{point.year}-W{point.week:02d}",
                reuse_count=reuse_weekly_counts[(point.year, point.week)],
            )
            for point in week_sequence
        ],
        top_categories=[
            LearningItemsCategoryCount(category=category, count=count)
            for category, count in category_counts.most_common(5)
        ],
        status_counts=[
            LearningItemsStatusCount(
                status=status,
                count=status_counts.get(status, 0),
            )
            for status in ("new", "in_progress", "applied", "ignored")
        ],
    )
