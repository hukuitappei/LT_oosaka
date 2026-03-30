import json

from fastapi import APIRouter, Request

from app.github.webhook import verify_signature
from app.services.webhook import process_github_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request):
    body = await verify_signature(request)
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)
    process_github_webhook(event_type, payload)
    return {"status": "accepted"}
