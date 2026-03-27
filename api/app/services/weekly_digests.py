from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WeeklyDigest
from app.llm import get_default_llm_provider


class WeeklyDigestNotFoundError(Exception):
    pass


class WeeklyDigestProviderUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class WeeklyDigestPeriod:
    year: int
    week: int


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
) -> list[WeeklyDigest]:
    result = await db.execute(
        select(WeeklyDigest)
        .where(WeeklyDigest.workspace_id == workspace_id)
        .order_by(WeeklyDigest.year.desc(), WeeklyDigest.week.desc())
    )
    return list(result.scalars().all())


def resolve_previous_week_period(*, today: date | None = None) -> WeeklyDigestPeriod:
    current_day = today or date.today()
    previous_week_day = current_day.fromordinal(current_day.toordinal() - 7)
    year, week, _ = previous_week_day.isocalendar()
    return WeeklyDigestPeriod(year=year, week=week)


async def get_workspace_weekly_digest(
    db: AsyncSession,
    digest_id: int,
    workspace_id: int,
) -> WeeklyDigest:
    digest = await db.scalar(
        select(WeeklyDigest).where(
            WeeklyDigest.id == digest_id,
            WeeklyDigest.workspace_id == workspace_id,
        )
    )
    if not digest:
        raise WeeklyDigestNotFoundError
    return digest


async def generate_workspace_weekly_digest(
    db: AsyncSession,
    workspace_id: int,
    *,
    year: int,
    week: int,
) -> WeeklyDigest:
    try:
        provider = get_default_llm_provider()
    except ValueError as exc:
        raise WeeklyDigestProviderUnavailableError(str(exc)) from exc

    from app.services.digest_generator import generate_weekly_digest

    return await generate_weekly_digest(year, week, workspace_id, provider, db)
