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

DIGEST_SYSTEM_PROMPT = """あなたはソフトウェアエンジニアの週次振り返りアシスタントです。
今週のPRレビューから抽出された学びを受け取り、週報としてまとめてください。

以下のJSONスキーマに厳密に従って出力してください。Markdownやコードブロックは使わず、JSONのみ返してください。

{
  "summary": "<今週の学びの全体サマリー（3〜5文）>",
  "repeated_issues": ["<繰り返し出てきた詰まりパターン>"],
  "next_time_notes": ["<来週の自分へのメモ>"]
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


def _build_digest_prompt(items: list[LearningItem], year: int, week: int) -> str:
    lines = [f"## {year}年 第{week}週の学び ({len(items)}件)", ""]
    by_category: dict[str, list[LearningItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    for category, cat_items in by_category.items():
        lines.append(f"### {category} ({len(cat_items)}件)")
        for item in cat_items:
            lines.append(f"- **{item.title}** (confidence: {item.confidence:.1f})")
            lines.append(f"  次回アクション: {item.action_for_next_time}")
        lines.append("")

    lines.append("上記の学びをもとに週報を生成してください。")
    return "\n".join(lines)


async def generate_weekly_digest(
    year: int,
    week: int,
    workspace_id: int,
    provider: BaseLLMProvider,
    db: AsyncSession,
) -> WeeklyDigest:
    items = await fetch_learning_items_for_week(year, week, workspace_id, db)

    if not items:
        summary = "今週はレビューから抽出された学びがありませんでした。"
        repeated_issues: list[str] = []
        next_time_notes: list[str] = []
    else:
        raw_result = await _call_llm_for_digest(_build_digest_prompt(items, year, week), provider)
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
        existing.pr_count = len(set(i.pull_request_id for i in items))
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
            pr_count=len(set(i.pull_request_id for i in items)),
            learning_count=len(items),
        )
        db.add(digest)

    await db.commit()
    await db.refresh(digest)
    return digest


async def _call_llm_for_digest(prompt: str, provider: BaseLLMProvider) -> dict:
    max_retries = 3
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            raw = await provider.generate_text(DIGEST_SYSTEM_PROMPT, prompt)
            return json.loads(raw)
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = 2.0 * (2 ** (attempt - 1))
                logger.warning(
                    "Digest LLM attempt %d/%d failed, retrying in %.1fs: %s",
                    attempt,
                    max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    logger.error("Digest LLM failed after %d attempts: %s", max_retries, last_exc)
    return {"summary": prompt[:200], "repeated_issues": [], "next_time_notes": []}
