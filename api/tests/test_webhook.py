import hashlib
import hmac
import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.github.webhook import verify_signature


class FakeRequest:
    def __init__(self, body: bytes, headers: dict[str, str]):
        self._body = body
        self.headers = headers

    async def body(self) -> bytes:
        return self._body


@pytest.mark.asyncio
async def test_verify_signature_accepts_valid_signature(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "secret", raising=False)
    body = b'{"ping":true}'
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    request = FakeRequest(body, {"X-Hub-Signature-256": signature})
    verified = await verify_signature(request)

    assert verified == body


@pytest.mark.asyncio
async def test_verify_signature_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "secret", raising=False)

    request = FakeRequest(b"{}", {"X-Hub-Signature-256": "sha256=bad"})

    with pytest.raises(HTTPException) as exc:
        await verify_signature(request)

    assert exc.value.status_code == 401


def test_process_github_webhook_enqueues_review_comment_via_celery(caplog):
    from app.services.webhook import process_github_webhook

    delay_mock = MagicMock()
    payload = {
        "action": "created",
        "pull_request": {"merged": True, "number": 42},
        "repository": {"full_name": "alice/repo"},
    }

    with caplog.at_level(logging.INFO):
        process_github_webhook(
            "pull_request_review_comment",
            payload,
            enqueue_task=delay_mock,
        )

    delay_mock.assert_called_once()
    assert payload == {
        "action": "created",
        "pull_request": {"merged": True, "number": 42},
        "repository": {"full_name": "alice/repo"},
    }
    enqueued_payload = delay_mock.call_args.args[0]
    assert enqueued_payload["event_type"] == "pull_request_review_comment"
    assert any(
        "Webhook received event_type=pull_request_review_comment action=created repo=alice/repo pr_number=42"
        in record.message
        for record in caplog.records
    )
    assert any(
        "Webhook enqueued Celery task task=extract_pr_task event_type=pull_request_review_comment action=created repo=alice/repo pr_number=42"
        in record.message
        for record in caplog.records
    )


def test_process_github_webhook_enqueues_merged_pull_request_via_celery(caplog):
    from app.services.webhook import process_github_webhook

    delay_mock = MagicMock()
    payload = {
        "action": "closed",
        "pull_request": {"merged": True, "number": 7},
        "repository": {"full_name": "alice/repo"},
        "installation": {"id": 99},
    }

    with caplog.at_level(logging.INFO):
        process_github_webhook(
            "pull_request",
            payload,
            enqueue_task=delay_mock,
        )

    delay_mock.assert_called_once()
    assert any(
        "Webhook enqueued Celery task task=extract_pr_task event_type=pull_request action=closed repo=alice/repo pr_number=7"
        in record.message
        for record in caplog.records
    )


def test_process_github_webhook_does_not_enqueue_irrelevant_event(caplog):
    from app.services.webhook import process_github_webhook

    delay_mock = MagicMock()
    payload = {
        "action": "opened",
        "pull_request": {"merged": False},
        "repository": {"full_name": "alice/repo"},
    }

    with caplog.at_level(logging.INFO):
        process_github_webhook("issues", payload, enqueue_task=delay_mock)

    delay_mock.assert_not_called()
    assert any(
        "Webhook ignored event_type=issues action=opened repo=alice/repo pr_number=None" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_github_webhook_delegates_to_service(monkeypatch):
    async def fake_verify_signature(request):
        return json.dumps({"action": "opened"}).encode("utf-8")

    from app.routers import webhook as routes

    process_mock = MagicMock()
    request = FakeRequest(b"", {"X-GitHub-Event": "issues"})

    monkeypatch.setattr(routes, "verify_signature", fake_verify_signature)
    monkeypatch.setattr(routes, "process_github_webhook", process_mock)

    response = await routes.github_webhook(request)

    process_mock.assert_called_once_with("issues", {"action": "opened"})
    assert response == {"status": "accepted"}
