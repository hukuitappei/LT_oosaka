import json
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.github.webhook import verify_signature
from app.services.pr_processor import process_pr_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await verify_signature(request)
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)

    if event_type in ("pull_request", "pull_request_review", "pull_request_review_comment"):
        action = payload.get("action", "")
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})

        # closed + merged or review submitted のときだけ処理
        if event_type == "pull_request" and action == "closed" and pr_data.get("merged"):
            background_tasks.add_task(process_pr_event, payload, db)
        elif event_type in ("pull_request_review", "pull_request_review_comment") and action == "submitted":
            background_tasks.add_task(process_pr_event, payload, db)

    return {"status": "accepted"}
