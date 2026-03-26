import hashlib
import hmac
from fastapi import HTTPException, Request
from app.config import settings


async def verify_signature(request: Request) -> bytes:
    """GitHub Webhook の署名を検証して body を返す"""
    body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256", "")

    if not settings.github_webhook_secret:
        return body  # 開発時はスキップ可

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return body
