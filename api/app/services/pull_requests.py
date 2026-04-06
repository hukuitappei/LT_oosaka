from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, PullRequest, Repository

logger = logging.getLogger(__name__)


class PullRequestNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class RelatedLearningItemMatch:
    item: LearningItem
    matched_terms: list[str]
    match_types: list[str]
    same_repository: bool
    score: int
    recommendation_reasons: list[str]


TOKEN_RE = re.compile(r"[a-z0-9_]{4,}")
STOP_WORDS = {
    "author",
    "this",
    "that",
    "with",
    "from",
    "into",
    "before",
    "after",
    "should",
    "would",
    "could",
    "there",
    "their",
    "about",
    "owner",
    "repo",
    "review",
    "request",
    "pull",
    "github",
    "have",
    "were",
    "when",
    "where",
    "validation",
}


def _tokenize(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if not value:
            continue
        for token in TOKEN_RE.findall(value.lower()):
            if token not in STOP_WORDS:
                tokens.add(token)
    return tokens


def _build_pr_context_tokens(pr: PullRequest) -> set[str]:
    return _pull_request_content_tokens(pr) | _pull_request_review_tokens(pr) | _pull_request_file_path_tokens(pr)


def _pull_request_content_tokens(pr: PullRequest | None) -> set[str]:
    if pr is None:
        return set()

    learning_tokens: set[str] = set()
    for item in pr.learning_items:
        learning_tokens |= _tokenize(
            item.title,
            item.detail,
            item.evidence,
            item.action_for_next_time,
            item.category,
        )

    return _tokenize(
        pr.title,
        pr.body,
        pr.author,
        pr.repository.full_name if pr.repository else None,
    ) | learning_tokens


def _pull_request_review_tokens(pr: PullRequest | None) -> set[str]:
    if pr is None:
        return set()

    review_tokens: set[str] = set()
    for comment in pr.review_comments:
        review_tokens |= _tokenize(
            comment.body,
            comment.diff_hunk,
        )
    return review_tokens


def _pull_request_file_path_tokens(pr: PullRequest | None) -> set[str]:
    if pr is None:
        return set()

    file_path_tokens: set[str] = set()
    for comment in pr.review_comments:
        file_path_tokens |= _tokenize(comment.file_path)
    return file_path_tokens


def _current_learning_categories(pr: PullRequest) -> set[str]:
    return {
        item.category
        for item in pr.learning_items
        if item.category
    }


def _status_score(status: str) -> int:
    if status == "applied":
        return 2
    if status == "in_progress":
        return 1
    if status == "ignored":
        return -2
    return 0


def _confidence_score(confidence: float) -> int:
    if confidence >= 0.95:
        return 2
    if confidence >= 0.8:
        return 1
    return 0


def _recency_score(created_at: datetime | None) -> int:
    if created_at is None:
        return 0
    now = datetime.now(timezone.utc)
    created = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    age_days = (now - created).days
    if age_days <= 30:
        return 2
    if age_days <= 90:
        return 1
    return 0


def _build_recommendation_reasons(
    matched_terms: list[str],
    same_repository: bool,
    category_aligned: bool,
    review_context_aligned: bool,
    status: str,
    created_at: datetime | None,
) -> list[str]:
    reasons: list[str] = []
    if same_repository:
        reasons.append("Same repository context")
    if category_aligned:
        reasons.append("Matches the current learning category")
    if review_context_aligned:
        reasons.append("Aligned with review comment context")
    if len(matched_terms) >= 3:
        reasons.append(f"Strong overlap on {len(matched_terms)} context terms")
    elif matched_terms:
        reasons.append(f"Overlap on {len(matched_terms)} context terms")
    if status == "applied":
        reasons.append("Previously marked as applied")
    elif status == "in_progress":
        reasons.append("Already being worked on")
    recency = _recency_score(created_at)
    if recency >= 2:
        reasons.append("Recent learning from the last 30 days")
    elif recency == 1:
        reasons.append("Recent learning from the last 90 days")
    return reasons


def _ranked_terms(*term_groups: set[str]) -> list[str]:
    combined = set().union(*term_groups)
    return sorted(combined, key=lambda term: (-len(term), term))


def _score_related_learning_items(
    pr: PullRequest,
    candidates: list[LearningItem],
) -> list[RelatedLearningItemMatch]:
    context_tokens = _build_pr_context_tokens(pr)
    if not context_tokens:
        return []
    current_categories = _current_learning_categories(pr)
    current_content_tokens = _pull_request_content_tokens(pr)
    current_review_tokens = _pull_request_review_tokens(pr)
    current_file_path_tokens = _pull_request_file_path_tokens(pr)

    matches: list[RelatedLearningItemMatch] = []
    for item in candidates:
        candidate_review_tokens = _pull_request_review_tokens(item.pull_request)
        candidate_content_tokens = _pull_request_content_tokens(item.pull_request) | _tokenize(
            item.title,
            item.detail,
            item.evidence,
            item.action_for_next_time,
            item.category,
        )
        candidate_file_path_tokens = _pull_request_file_path_tokens(item.pull_request)
        candidate_tokens = candidate_content_tokens | candidate_review_tokens | candidate_file_path_tokens
        content_overlap = current_content_tokens & candidate_content_tokens
        review_overlap = current_review_tokens & candidate_review_tokens
        file_path_overlap = current_file_path_tokens & candidate_file_path_tokens
        matched_terms = _ranked_terms(review_overlap, file_path_overlap, content_overlap)
        if not matched_terms:
            continue

        match_types: list[str] = []
        if content_overlap:
            match_types.append("content_match")
        if review_overlap:
            match_types.append("review_match")
        if file_path_overlap:
            match_types.append("file_path_match")

        same_repository = (
            pr.repository is not None
            and item.pull_request is not None
            and item.pull_request.repository is not None
            and item.pull_request.repository.id == pr.repository.id
        )
        category_aligned = item.category in current_categories
        review_context_aligned = bool(review_overlap or file_path_overlap)
        if not same_repository and len(matched_terms) < 2:
            continue
        if (
            not same_repository
            and not category_aligned
            and not review_context_aligned
            and len(content_overlap) < 4
        ):
            continue
        score = (
            len(matched_terms)
            + (3 if same_repository else 0)
            + (2 if category_aligned else 0)
            + (2 if review_context_aligned else 0)
            + _status_score(item.status)
            + _confidence_score(item.confidence)
            + _recency_score(item.created_at)
        )
        recommendation_reasons = _build_recommendation_reasons(
            matched_terms=matched_terms,
            same_repository=same_repository,
            category_aligned=category_aligned,
            review_context_aligned=review_context_aligned,
            status=item.status,
            created_at=item.created_at,
        )
        matches.append(
            RelatedLearningItemMatch(
                item=item,
                matched_terms=matched_terms[:5],
                match_types=match_types,
                same_repository=same_repository,
                score=score,
                recommendation_reasons=recommendation_reasons,
            )
        )

    matches.sort(
        key=lambda match: (
            -match.score,
            match.item.status == "ignored",
            -match.item.confidence,
            -match.item.id,
        )
    )
    return matches[:3]


async def get_workspace_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
) -> PullRequest | None:
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(PullRequest.learning_items),
            selectinload(PullRequest.repository),
            selectinload(PullRequest.review_comments),
        )
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


async def get_related_learning_items_for_pull_request(
    db: AsyncSession,
    pr: PullRequest,
    workspace_id: int,
) -> list[RelatedLearningItemMatch]:
    result = await db.execute(
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(LearningItem.pull_request).selectinload(PullRequest.repository),
            selectinload(LearningItem.pull_request).selectinload(PullRequest.learning_items),
            selectinload(LearningItem.pull_request).selectinload(PullRequest.review_comments),
        )
        .where(
            LearningItem.workspace_id == workspace_id,
            LearningItem.pull_request_id != pr.id,
        )
        .order_by(LearningItem.created_at.desc())
    )
    return _score_related_learning_items(pr, list(result.scalars().all()))


async def request_reanalysis_for_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
    user_id: int,
) -> dict[str, int | str]:
    pr = await get_workspace_pull_request(db, pr_id, workspace_id)
    if not pr:
        raise PullRequestNotFoundError

    from app.tasks.extract import reanalyze_pr_task

    reanalyze_pr_task.delay(pr.id, workspace_id, user_id)
    logger.info(
        "request_reanalysis_for_pull_request enqueued pr_id=%d workspace_id=%d user_id=%d",
        pr.id,
        workspace_id,
        user_id,
    )
    return {"status": "accepted", "pr_id": pr_id}
