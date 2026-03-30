from __future__ import annotations

import logging
from collections.abc import Callable

from app.tasks.extract import extract_pr_task

logger = logging.getLogger(__name__)


def build_webhook_correlation_id(event_type: str, payload: dict) -> str:
    action = payload.get("action", "") or "unknown"
    repo = payload.get("repository", {}).get("full_name", "") or "unknown"
    pr_number = payload.get("pull_request", {}).get("number")
    installation_id = payload.get("installation", {}).get("id")
    pr_part = "na" if pr_number is None else str(pr_number)
    installation_part = "na" if installation_id is None else str(installation_id)
    return f"github-webhook:{event_type or 'unknown'}:{action}:{repo}:{pr_part}:{installation_part}"


def build_webhook_context(event_type: str, payload: dict) -> dict[str, object]:
    action = payload.get("action", "")
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})
    installation_id = payload.get("installation", {}).get("id")
    correlation_id = payload.get("correlation_id") or build_webhook_correlation_id(event_type, payload)

    return {
        "event_type": event_type,
        "action": action,
        "repo": repo_data.get("full_name", ""),
        "pr_number": pr_data.get("number"),
        "installation_id": installation_id,
        "correlation_id": correlation_id,
    }


def should_enqueue_webhook(event_type: str, payload: dict) -> bool:
    action = payload.get("action", "")
    pr_data = payload.get("pull_request", {})

    if event_type == "pull_request":
        return action == "closed" and bool(pr_data.get("merged"))
    if event_type == "pull_request_review":
        return action == "submitted"
    if event_type == "pull_request_review_comment":
        return action in {"created", "edited"}
    return False


def process_github_webhook(
    event_type: str,
    payload: dict,
    *,
    enqueue_task: Callable[[dict], object] = extract_pr_task.delay,
) -> None:
    payload = dict(payload)
    payload["event_type"] = event_type
    payload["correlation_id"] = build_webhook_correlation_id(event_type, payload)

    context = build_webhook_context(event_type, payload)
    should_enqueue = should_enqueue_webhook(event_type, payload)

    logger.info(
        "Webhook received event_type=%s action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s should_enqueue=%s",
        context["event_type"],
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        context["correlation_id"],
        should_enqueue,
    )
    if should_enqueue:
        enqueue_task(payload)
        logger.info(
            "Webhook enqueued Celery task task=extract_pr_task event_type=%s action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
            context["event_type"],
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
        )
    else:
        logger.info(
            "Webhook ignored event_type=%s action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
            context["event_type"],
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
        )
