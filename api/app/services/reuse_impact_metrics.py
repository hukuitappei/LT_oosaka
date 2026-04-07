from __future__ import annotations

from dataclasses import dataclass

from app.db.models import LearningItem, LearningReuseEvent, PullRequest
from app.services.related_learning_recommendations import (
    pull_request_file_path_tokens,
    pull_request_review_tokens,
    tokenize,
)


@dataclass(frozen=True)
class ReuseImpactSummary:
    total_reuse_events: int
    reused_learning_items_count: int
    recurring_reuse_events: int
    clean_reuse_events: int


def build_reuse_impact_summary(events: list[LearningReuseEvent]) -> ReuseImpactSummary:
    recurring_reuse_events = 0
    reused_learning_item_ids: set[int] = set()

    for event in events:
        reused_learning_item_ids.add(event.source_learning_item_id)
        if reuse_event_has_recurrence(event):
            recurring_reuse_events += 1

    total_reuse_events = len(events)
    return ReuseImpactSummary(
        total_reuse_events=total_reuse_events,
        reused_learning_items_count=len(reused_learning_item_ids),
        recurring_reuse_events=recurring_reuse_events,
        clean_reuse_events=total_reuse_events - recurring_reuse_events,
    )


def reuse_event_has_recurrence(event: LearningReuseEvent) -> bool:
    if event.source_learning_item is None or event.target_pull_request is None:
        return False

    source_tokens = build_reuse_source_tokens(event.source_learning_item)
    if not source_tokens:
        return False

    target_review_tokens = build_target_review_tokens(event.target_pull_request)
    return bool(source_tokens & target_review_tokens)


def build_reuse_source_tokens(item: LearningItem) -> set[str]:
    source_pr = item.pull_request
    return tokenize(
        item.title,
        item.detail,
        item.evidence,
        item.action_for_next_time,
        item.category,
    ) | pull_request_review_tokens(source_pr) | pull_request_file_path_tokens(source_pr)


def build_target_review_tokens(pr: PullRequest) -> set[str]:
    return pull_request_review_tokens(pr) | pull_request_file_path_tokens(pr)
