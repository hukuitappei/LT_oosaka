from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, LearningReuseEvent, PullRequest, WeeklyDigest
from app.llm import get_default_llm_provider
from app.services.reuse_impact_metrics import build_reuse_impact_summary


class WeeklyDigestNotFoundError(Exception):
    pass


class WeeklyDigestProviderUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class WeeklyDigestPeriod:
    year: int
    week: int


@dataclass(frozen=True)
class WeeklyDigestView:
    id: int
    workspace_id: int
    year: int
    week: int
    summary: str
    repeated_issues: list[str]
    next_time_notes: list[str]
    pr_count: int
    learning_count: int
    reuse_event_count: int
    reused_learning_item_count: int
    recurring_reuse_event_count: int
    clean_reuse_event_count: int
    visibility: str
    created_at: datetime


def resolve_weekly_digest_period(
    requested_year: int | None,
    requested_week: int | None,
    *,
    today: date | None = None,
) -> WeeklyDigestPeriod:
    current_day = today or date.today()
    current_year, current_week, _ = current_day.isocalendar()
    return WeeklyDigestPeriod(
        year=requested_year or current_year,
        week=requested_week or current_week,
    )


async def list_workspace_weekly_digests(
    db: AsyncSession,
    workspace_id: int,
) -> list[WeeklyDigestView]:
    result = await db.execute(
        select(WeeklyDigest)
        .where(WeeklyDigest.workspace_id == workspace_id)
        .order_by(WeeklyDigest.year.desc(), WeeklyDigest.week.desc())
    )
    digests = list(result.scalars().all())
    return [await _build_weekly_digest_view(db, digest) for digest in digests]


def resolve_previous_week_period(*, today: date | None = None) -> WeeklyDigestPeriod:
    current_day = today or date.today()
    previous_week_day = current_day.fromordinal(current_day.toordinal() - 7)
    year, week, _ = previous_week_day.isocalendar()
    return WeeklyDigestPeriod(year=year, week=week)


async def get_workspace_weekly_digest(
    db: AsyncSession,
    digest_id: int,
    workspace_id: int,
) -> WeeklyDigestView:
    digest = await db.scalar(
        select(WeeklyDigest).where(
            WeeklyDigest.id == digest_id,
            WeeklyDigest.workspace_id == workspace_id,
        )
    )
    if not digest:
        raise WeeklyDigestNotFoundError
    return await _build_weekly_digest_view(db, digest)


async def generate_workspace_weekly_digest(
    db: AsyncSession,
    workspace_id: int,
    *,
    year: int,
    week: int,
) -> WeeklyDigestView:
    try:
        provider = get_default_llm_provider()
    except ValueError as exc:
        raise WeeklyDigestProviderUnavailableError(str(exc)) from exc

    from app.services.digest_generator import generate_weekly_digest

    digest = await generate_weekly_digest(year, week, workspace_id, provider, db)
    return await _build_weekly_digest_view(db, digest)


async def _build_weekly_digest_view(
    db: AsyncSession,
    digest: WeeklyDigest,
) -> WeeklyDigestView:
    (
        reuse_event_count,
        reused_learning_item_count,
        recurring_reuse_event_count,
        clean_reuse_event_count,
    ) = await _fetch_reuse_metrics_for_period(
        db,
        digest.workspace_id,
        digest.year,
        digest.week,
    )
    return WeeklyDigestView(
        id=digest.id,
        workspace_id=digest.workspace_id,
        year=digest.year,
        week=digest.week,
        summary=digest.summary,
        repeated_issues=digest.repeated_issues,
        next_time_notes=digest.next_time_notes,
        pr_count=digest.pr_count,
        learning_count=digest.learning_count,
        reuse_event_count=reuse_event_count,
        reused_learning_item_count=reused_learning_item_count,
        recurring_reuse_event_count=recurring_reuse_event_count,
        clean_reuse_event_count=clean_reuse_event_count,
        visibility=digest.visibility,
        created_at=digest.created_at,
    )


async def _fetch_reuse_metrics_for_period(
    db: AsyncSession,
    workspace_id: int,
    year: int,
    week: int,
) -> tuple[int, int, int, int]:
    from app.services.digest_generator import _get_week_range

    week_start, week_end = _get_week_range(year, week)
    result = await db.execute(
        select(LearningReuseEvent)
        .where(
            LearningReuseEvent.workspace_id == workspace_id,
            LearningReuseEvent.created_at >= week_start,
            LearningReuseEvent.created_at <= week_end,
        )
        .options(
            selectinload(LearningReuseEvent.source_learning_item)
            .selectinload(LearningItem.pull_request)
            .selectinload(PullRequest.review_comments),
            selectinload(LearningReuseEvent.target_pull_request).selectinload(PullRequest.review_comments),
        )
    )
    reuse_events = list(result.scalars().all())
    summary = build_reuse_impact_summary(reuse_events)
    return (
        summary.total_reuse_events,
        summary.reused_learning_items_count,
        summary.recurring_reuse_events,
        summary.clean_reuse_events,
    )
