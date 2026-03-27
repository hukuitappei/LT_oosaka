import json
import logging

from fastapi import APIRouter, Request

from app.github.webhook import verify_signature
from app.tasks.extract import extract_pr_task

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def _webhook_context(event_type: str, payload: dict) -> dict[str, object]:
    action = payload.get("action", "")
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})
    installation_id = payload.get("installation", {}).get("id")

    return {
        "event_type": event_type,
        "action": action,
        "repo": repo_data.get("full_name", ""),
        "pr_number": pr_data.get("number"),
        "installation_id": installation_id,
    }


def _should_enqueue(event_type: str, payload: dict) -> bool:
    action = payload.get("action", "")
    pr_data = payload.get("pull_request", {})

    if event_type == "pull_request":
        return action == "closed" and bool(pr_data.get("merged"))
    if event_type == "pull_request_review":
        return action == "submitted"
    if event_type == "pull_request_review_comment":
        return action in {"created", "edited"}
    return False


@router.post("/github")
async def github_webhook(request: Request):
    body = await verify_signature(request)
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)
    payload["event_type"] = event_type
    context = _webhook_context(event_type, payload)
    should_enqueue = _should_enqueue(event_type, payload)

    logger.info(
        "Webhook received event_type=%s action=%s repo=%s pr_number=%s installation_id=%s should_enqueue=%s",
        context["event_type"],
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        should_enqueue,
    )
    if should_enqueue:
        extract_pr_task.delay(payload)
        logger.info(
            "Webhook enqueued Celery task task=extract_pr_task event_type=%s action=%s repo=%s pr_number=%s installation_id=%s",
            context["event_type"],
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
        )
    else:
        logger.info(
            "Webhook ignored event_type=%s action=%s repo=%s pr_number=%s installation_id=%s",
            context["event_type"],
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
        )

    return {"status": "accepted"}
