from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningItem, WeeklyDigest
from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

DIGEST_SYSTEM_PROMPT = """You are a weekly review assistant for software engineers.
Read the provided learning items and return JSON only.
Do not output Markdown or code blocks.

{
  "summary": "<2-4 sentences summarizing the week's learning>",
  "repeated_issues": ["<recurring issues or patterns>"],
  "next_time_notes": ["<specific notes for next time>"]
}"""


def _get_week_range(year: int, week: int) -> tuple[date, date]:
    jan4 = date(year, 1, 4)
    week_start = jan4 + timedelta(weeks=week - 1) - timedelta(days=jan4.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


async def fetch_learning_items_for_week(
    year: int,
    week: int,
    workspace_id: int,
    db: AsyncSession,
) -> list[LearningItem]:
    week_start, week_end = _get_week_range(year, week)
    result = await db.execute(
        select(LearningItem)
        .where(
            LearningItem.workspace_id == workspace_id,
            LearningItem.created_at >= week_start,
            LearningItem.created_at <= week_end,
            LearningItem.visibility.in_(("private_draft", "workspace_shared")),
        )
        .order_by(LearningItem.category, LearningItem.confidence.desc())
    )
    return list(result.scalars().all())


async def fetch_learning_reuse_metrics_for_week(
    year: int,
    week: int,
    workspace_id: int,
    db: AsyncSession,
) -> tuple[int, int]:
    from app.services.weekly_digests import _fetch_reuse_metrics_for_period

    reuse_event_count, reused_learning_item_count, _, _ = await _fetch_reuse_metrics_for_period(
        db, workspace_id, year, week
    )
    return reuse_event_count, reused_learning_item_count


def _build_digest_prompt(
    items: list[LearningItem],
    year: int,
    week: int,
    *,
    reuse_event_count: int,
    reused_learning_item_count: int,
    recurring_reuse_event_count: int,
    clean_reuse_event_count: int,
) -> str:
    lines = [f"## {year} Week {week} learning items ({len(items)} items)", ""]
    by_category: dict[str, list[LearningItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    for category, cat_items in by_category.items():
        lines.append(f"### {category} ({len(cat_items)} items)")
        for item in cat_items:
            lines.append(f"- **{item.title}** (confidence: {item.confidence:.1f})")
            lines.append(f"  Next action: {item.action_for_next_time}")
        lines.append("")

    lines.append("## Reuse signals")
    lines.append(f"- Reuse events recorded this week: {reuse_event_count}")
    lines.append(f"- Unique learning items reused this week: {reused_learning_item_count}")
    lines.append(f"- Repeated review signals after reuse: {recurring_reuse_event_count}")
    lines.append(f"- Clean reuses without repeated review signals: {clean_reuse_event_count}")
    lines.append("")
    lines.append("Summarize the weekly reflection based on the learning items above.")
    return "\n".join(lines)


def _digest_pr_identity(item: LearningItem) -> str | int | None:
    if item.pull_request_id is not None:
        return item.pull_request_id
    if item.source_repository_full_name and item.source_github_pr_number is not None:
        return f"{item.source_repository_full_name}#{item.source_github_pr_number}"
    return None


async def generate_weekly_digest(
    year: int,
    week: int,
    workspace_id: int,
    provider: BaseLLMProvider,
    db: AsyncSession,
) -> WeeklyDigest:
    items = await fetch_learning_items_for_week(year, week, workspace_id, db)
    from app.services.weekly_digests import _fetch_reuse_metrics_for_period

    (
        reuse_event_count,
        reused_learning_item_count,
        recurring_reuse_event_count,
        clean_reuse_event_count,
    ) = await _fetch_reuse_metrics_for_period(db, workspace_id, year, week)
    logger.info(
        "generate_weekly_digest started workspace_id=%d year=%d week=%d item_count=%d reuse_event_count=%d reused_learning_item_count=%d recurring_reuse_event_count=%d clean_reuse_event_count=%d",
        workspace_id,
        year,
        week,
        len(items),
        reuse_event_count,
        reused_learning_item_count,
        recurring_reuse_event_count,
        clean_reuse_event_count,
    )

    if not items:
        summary = "No learning items were extracted from reviews this week yet."
        repeated_issues: list[str] = []
        next_time_notes: list[str] = []
    else:
        logger.info(
            "generate_weekly_digest calling LLM workspace_id=%d year=%d week=%d item_count=%d",
            workspace_id,
            year,
            week,
            len(items),
        )
        raw_result = await _call_llm_for_digest(
            _build_digest_prompt(
                items,
                year,
                week,
                reuse_event_count=reuse_event_count,
                reused_learning_item_count=reused_learning_item_count,
                recurring_reuse_event_count=recurring_reuse_event_count,
                clean_reuse_event_count=clean_reuse_event_count,
            ),
            provider,
            workspace_id=workspace_id,
            year=year,
            week=week,
            item_count=len(items),
        )
        summary = raw_result.get("summary", "")
        repeated_issues = raw_result.get("repeated_issues", [])
        next_time_notes = raw_result.get("next_time_notes", [])

    existing = await db.scalar(
        select(WeeklyDigest).where(
            WeeklyDigest.workspace_id == workspace_id,
            WeeklyDigest.year == year,
            WeeklyDigest.week == week,
        )
    )
    if existing:
        existing.summary = summary
        existing.repeated_issues = repeated_issues
        existing.next_time_notes = next_time_notes
        existing.pr_count = len({identity for identity in (_digest_pr_identity(i) for i in items) if identity is not None})
        existing.learning_count = len(items)
        digest = existing
    else:
        digest = WeeklyDigest(
            workspace_id=workspace_id,
            visibility="workspace_shared",
            year=year,
            week=week,
            summary=summary,
            repeated_issues=repeated_issues,
            next_time_notes=next_time_notes,
            pr_count=len({identity for identity in (_digest_pr_identity(i) for i in items) if identity is not None}),
            learning_count=len(items),
        )
        db.add(digest)

    await db.commit()
    await db.refresh(digest)
    logger.info(
        "generate_weekly_digest saved workspace_id=%d year=%d week=%d digest_id=%d pr_count=%d learning_count=%d",
        workspace_id,
        year,
        week,
        digest.id,
        digest.pr_count,
        digest.learning_count,
    )
    return digest


async def _call_llm_for_digest(
    prompt: str,
    provider: BaseLLMProvider,
    *,
    workspace_id: int | None = None,
    year: int | None = None,
    week: int | None = None,
    item_count: int | None = None,
) -> dict:
    max_retries = 3
    last_exc: Exception | None = None
    context_bits = []
    if workspace_id is not None:
        context_bits.append(f"workspace_id={workspace_id}")
    if year is not None:
        context_bits.append(f"year={year}")
    if week is not None:
        context_bits.append(f"week={week}")
    if item_count is not None:
        context_bits.append(f"item_count={item_count}")
    context_suffix = f" [{' '.join(context_bits)}]" if context_bits else ""

    for attempt in range(1, max_retries + 1):
        try:
            raw = await provider.generate_text(DIGEST_SYSTEM_PROMPT, prompt)
            return json.loads(raw)
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = 2.0 * (2 ** (attempt - 1))
                logger.warning(
                    "Digest LLM attempt %d/%d failed%s, retrying in %.1fs: %s",
                    attempt,
                    max_retries,
                    context_suffix,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    logger.error("Digest LLM failed after %d attempts%s: %s", max_retries, context_suffix, last_exc)
    return {"summary": prompt[:200], "repeated_issues": [], "next_time_notes": []}
