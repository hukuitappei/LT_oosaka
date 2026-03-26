import hashlib
import hmac
import logging
from fastapi import HTTPException, Request
from app.config import settings

logger = logging.getLogger(__name__)


async def verify_signature(request: Request) -> bytes:
    """GitHub Webhook の署名を検証して body を返す"""
    body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256", "")

    if not settings.github_webhook_secret:
        if settings.app_env == "development":
            logger.warning("Webhook signature verification skipped (development mode)")
            return body
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured",
        )

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return body
