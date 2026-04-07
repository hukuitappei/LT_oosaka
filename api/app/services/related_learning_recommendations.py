from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.db.models import LearningItem, PullRequest


@dataclass(frozen=True)
class RelatedLearningItemMatch:
    item: LearningItem
    matched_terms: list[str]
    match_types: list[str]
    same_repository: bool
    score: int
    recommendation_reasons: list[str]
    reuse_count: int = 0
    reused_in_current_pr: bool = False


@dataclass(frozen=True)
class PullRequestTokenContext:
    content_tokens: set[str]
    review_tokens: set[str]
    file_path_tokens: set[str]

    @property
    def all_tokens(self) -> set[str]:
        return self.content_tokens | self.review_tokens | self.file_path_tokens


@dataclass(frozen=True)
class RelatedLearningCandidate:
    item: LearningItem
    token_context: PullRequestTokenContext
    same_repository: bool
    category_aligned: bool


@dataclass(frozen=True)
class RecommendationOverlap:
    content_overlap: set[str]
    review_overlap: set[str]
    file_path_overlap: set[str]

    @property
    def matched_terms(self) -> list[str]:
        return ranked_terms(self.review_overlap, self.file_path_overlap, self.content_overlap)

    @property
    def match_types(self) -> list[str]:
        types: list[str] = []
        if self.content_overlap:
            types.append("content_match")
        if self.review_overlap:
            types.append("review_match")
        if self.file_path_overlap:
            types.append("file_path_match")
        return types

    @property
    def review_context_aligned(self) -> bool:
        return bool(self.review_overlap or self.file_path_overlap)


@dataclass(frozen=True)
class RecurrenceSignals:
    matched_terms: list[str]
    match_types: list[str]
    review_context_aligned: bool
    content_overlap_size: int

    @property
    def has_match(self) -> bool:
        return bool(self.matched_terms)


@dataclass(frozen=True)
class RecommendationExplanationInput:
    matched_terms: list[str]
    same_repository: bool
    category_aligned: bool
    review_context_aligned: bool
    status: str
    created_at: datetime | None


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


def tokenize(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if not value:
            continue
        for token in TOKEN_RE.findall(value.lower()):
            if token not in STOP_WORDS:
                tokens.add(token)
    return tokens


def pull_request_content_tokens(pr: PullRequest | None) -> set[str]:
    if pr is None:
        return set()

    learning_tokens: set[str] = set()
    for item in pr.learning_items:
        learning_tokens |= tokenize(
            item.title,
            item.detail,
            item.evidence,
            item.action_for_next_time,
            item.category,
        )

    return tokenize(
        pr.title,
        pr.body,
        pr.author,
        pr.repository.full_name if pr.repository else None,
    ) | learning_tokens


def pull_request_review_tokens(pr: PullRequest | None) -> set[str]:
    if pr is None:
        return set()

    review_tokens: set[str] = set()
    for comment in pr.review_comments:
        review_tokens |= tokenize(comment.body, comment.diff_hunk)
    return review_tokens


def pull_request_file_path_tokens(pr: PullRequest | None) -> set[str]:
    if pr is None:
        return set()

    file_path_tokens: set[str] = set()
    for comment in pr.review_comments:
        file_path_tokens |= tokenize(comment.file_path)
    return file_path_tokens


def build_pull_request_token_context(pr: PullRequest | None) -> PullRequestTokenContext:
    return PullRequestTokenContext(
        content_tokens=pull_request_content_tokens(pr),
        review_tokens=pull_request_review_tokens(pr),
        file_path_tokens=pull_request_file_path_tokens(pr),
    )


def current_learning_categories(pr: PullRequest) -> set[str]:
    return {item.category for item in pr.learning_items if item.category}


def build_related_learning_candidates_for_pull_request(
    pr: PullRequest,
    candidates: list[LearningItem],
) -> list[RelatedLearningCandidate]:
    categories = current_learning_categories(pr)
    return [
        RelatedLearningCandidate(
            item=item,
            token_context=build_candidate_context(item),
            same_repository=is_same_repository(pr, item),
            category_aligned=item.category in categories,
        )
        for item in candidates
    ]


def build_candidate_context(item: LearningItem) -> PullRequestTokenContext:
    return PullRequestTokenContext(
        content_tokens=pull_request_content_tokens(item.pull_request)
        | tokenize(
            item.title,
            item.detail,
            item.evidence,
            item.action_for_next_time,
            item.category,
        ),
        review_tokens=pull_request_review_tokens(item.pull_request),
        file_path_tokens=pull_request_file_path_tokens(item.pull_request),
    )


def is_same_repository(pr: PullRequest, item: LearningItem) -> bool:
    return (
        pr.repository is not None
        and item.pull_request is not None
        and item.pull_request.repository is not None
        and item.pull_request.repository.id == pr.repository.id
    )


def build_recommendation_overlap(
    current_context: PullRequestTokenContext,
    candidate_context: PullRequestTokenContext,
) -> RecommendationOverlap:
    return RecommendationOverlap(
        content_overlap=current_context.content_tokens & candidate_context.content_tokens,
        review_overlap=current_context.review_tokens & candidate_context.review_tokens,
        file_path_overlap=current_context.file_path_tokens & candidate_context.file_path_tokens,
    )


def detect_recurrence_signals(overlap: RecommendationOverlap) -> RecurrenceSignals:
    return RecurrenceSignals(
        matched_terms=overlap.matched_terms,
        match_types=overlap.match_types,
        review_context_aligned=overlap.review_context_aligned,
        content_overlap_size=len(overlap.content_overlap),
    )


def status_score(status: str) -> int:
    if status == "applied":
        return 2
    if status == "in_progress":
        return 1
    if status == "ignored":
        return -2
    return 0


def confidence_score(confidence: float) -> int:
    if confidence >= 0.95:
        return 2
    if confidence >= 0.8:
        return 1
    return 0


def recency_score(created_at: datetime | None) -> int:
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


def build_recommendation_explanation(
    explanation: RecommendationExplanationInput,
) -> list[str]:
    reasons: list[str] = []
    if explanation.same_repository:
        reasons.append("Same repository context")
    if explanation.category_aligned:
        reasons.append("Matches the current learning category")
    if explanation.review_context_aligned:
        reasons.append("Aligned with review comment context")
    if len(explanation.matched_terms) >= 3:
        reasons.append(f"Strong overlap on {len(explanation.matched_terms)} context terms")
    elif explanation.matched_terms:
        reasons.append(f"Overlap on {len(explanation.matched_terms)} context terms")
    if explanation.status == "applied":
        reasons.append("Previously marked as applied")
    elif explanation.status == "in_progress":
        reasons.append("Already being worked on")
    recency = recency_score(explanation.created_at)
    if recency >= 2:
        reasons.append("Recent learning from the last 30 days")
    elif recency == 1:
        reasons.append("Recent learning from the last 90 days")
    return reasons


def ranked_terms(*term_groups: set[str]) -> list[str]:
    combined = set().union(*term_groups)
    return sorted(combined, key=lambda term: (-len(term), term))


def is_candidate_eligible(
    signals: RecurrenceSignals,
    *,
    same_repository: bool,
    category_aligned: bool,
) -> bool:
    if not signals.has_match:
        return False
    if not same_repository and len(signals.matched_terms) < 2:
        return False
    if (
        not same_repository
        and not category_aligned
        and not signals.review_context_aligned
        and signals.content_overlap_size < 4
    ):
        return False
    return True


def score_candidate(
    item: LearningItem,
    signals: RecurrenceSignals,
    *,
    same_repository: bool,
    category_aligned: bool,
) -> int:
    return (
        len(signals.matched_terms)
        + (3 if same_repository else 0)
        + (2 if category_aligned else 0)
        + (2 if signals.review_context_aligned else 0)
        + status_score(item.status)
        + confidence_score(item.confidence)
        + recency_score(item.created_at)
    )


def rank_matches(matches: list[RelatedLearningItemMatch]) -> list[RelatedLearningItemMatch]:
    matches.sort(
        key=lambda match: (
            -match.score,
            match.item.status == "ignored",
            -match.item.confidence,
            -match.item.id,
        )
    )
    return matches[:3]


def recommend_related_learning_items(
    pr: PullRequest,
    candidates: list[LearningItem],
) -> list[RelatedLearningItemMatch]:
    current_context = build_pull_request_token_context(pr)
    if not current_context.all_tokens:
        return []

    matches: list[RelatedLearningItemMatch] = []
    for candidate in build_related_learning_candidates_for_pull_request(pr, candidates):
        item = candidate.item
        overlap = build_recommendation_overlap(current_context, candidate.token_context)
        signals = detect_recurrence_signals(overlap)

        if not is_candidate_eligible(
            signals,
            same_repository=candidate.same_repository,
            category_aligned=candidate.category_aligned,
        ):
            continue

        matched_terms = signals.matched_terms
        matches.append(
            RelatedLearningItemMatch(
                item=item,
                matched_terms=matched_terms[:5],
                match_types=signals.match_types,
                same_repository=candidate.same_repository,
                score=score_candidate(
                    item,
                    signals,
                    same_repository=candidate.same_repository,
                    category_aligned=candidate.category_aligned,
                ),
                recommendation_reasons=build_recommendation_explanation(
                    RecommendationExplanationInput(
                        matched_terms=matched_terms,
                        same_repository=candidate.same_repository,
                        category_aligned=candidate.category_aligned,
                        review_context_aligned=signals.review_context_aligned,
                        status=item.status,
                        created_at=item.created_at,
                    )
                ),
            )
        )

    return rank_matches(matches)
