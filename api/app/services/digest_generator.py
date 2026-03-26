import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import LearningItem, PullRequest, WeeklyDigest
from app.llm.base import BaseLLMProvider
from app.schemas.llm_output import LLMOutputV1

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
    """ISO週番号から月曜〜日曜の範囲を返す"""
    jan4 = date(year, 1, 4)
    week_start = jan4 + timedelta(weeks=week - 1) - timedelta(days=jan4.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


async def fetch_learning_items_for_week(
    year: int, week: int, db: AsyncSession
) -> list[LearningItem]:
    """指定週の learning_items を取得する"""
    week_start, week_end = _get_week_range(year, week)
    result = await db.execute(
        select(LearningItem)
        .where(
            LearningItem.created_at >= week_start,
            LearningItem.created_at <= week_end,
        )
        .order_by(LearningItem.category, LearningItem.confidence.desc())
    )
    return list(result.scalars().all())


def _build_digest_prompt(items: list[LearningItem], year: int, week: int) -> str:
    lines = [
        f"## {year}年 第{week}週の学び ({len(items)}件)",
        "",
    ]
    # カテゴリ別にグループ化
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
    year: int, week: int, provider: BaseLLMProvider, db: AsyncSession
) -> WeeklyDigest:
    """週報を生成してDBに保存する"""
    items = await fetch_learning_items_for_week(year, week, db)

    if not items:
        summary = "今週はレビューから抽出された学びがありませんでした。"
        repeated_issues: list[str] = []
        next_time_notes: list[str] = []
    else:
        prompt = _build_digest_prompt(items, year, week)
        import json
        import anthropic as _anthropic

        # LLM呼び出し（digest用の簡易プロンプト）
        raw_result = await _call_llm_for_digest(prompt, provider)
        summary = raw_result.get("summary", "")
        repeated_issues = raw_result.get("repeated_issues", [])
        next_time_notes = raw_result.get("next_time_notes", [])

    # 既存レコードがあれば更新
    existing = await db.scalar(
        select(WeeklyDigest).where(
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
    """週報生成用LLM呼び出し（extract_learnings を流用）"""
    import json
    # provider の extract_learnings は LLMOutputV1 を返すが、
    # digest では別プロンプトで直接 JSON を取得する
    # AnthropicProvider / OllamaProvider の内部クライアントを使う
    try:
        from app.llm.anthropic_provider import AnthropicProvider
        if isinstance(provider, AnthropicProvider):
            import anthropic
            message = provider.client.messages.create(
                model=provider.model,
                max_tokens=1024,
                system=DIGEST_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return json.loads(message.content[0].text.strip())
    except Exception:
        pass

    try:
        from app.llm.ollama_provider import OllamaProvider
        if isinstance(provider, OllamaProvider):
            response = provider.client.chat(
                model=provider.model,
                messages=[
                    {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                format="json",
            )
            return json.loads(response.message.content.strip())
    except Exception:
        pass

    return {"summary": prompt[:200], "repeated_issues": [], "next_time_notes": []}
