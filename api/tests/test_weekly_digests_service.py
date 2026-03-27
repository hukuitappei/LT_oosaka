import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_list_workspace_weekly_digests_returns_descending_order(db_session):
    from app.db.models import WeeklyDigest
    from app.services.weekly_digests import list_workspace_weekly_digests

    db_session.add_all(
        [
            WeeklyDigest(workspace_id=1, year=2026, week=10, summary="older"),
            WeeklyDigest(workspace_id=1, year=2026, week=12, summary="newer"),
            WeeklyDigest(workspace_id=2, year=2026, week=15, summary="other"),
        ]
    )
    await db_session.commit()

    digests = await list_workspace_weekly_digests(db_session, 1)

    assert [(digest.year, digest.week) for digest in digests] == [(2026, 12), (2026, 10)]


@pytest.mark.asyncio
async def test_get_workspace_weekly_digest_filters_by_workspace(db_session):
    from app.db.models import WeeklyDigest
    from app.services.weekly_digests import (
        WeeklyDigestNotFoundError,
        get_workspace_weekly_digest,
    )

    digest = WeeklyDigest(workspace_id=1, year=2026, week=12, summary="summary")
    db_session.add(digest)
    await db_session.commit()

    found = await get_workspace_weekly_digest(db_session, digest.id, 1)
    assert found.id == digest.id

    with pytest.raises(WeeklyDigestNotFoundError):
        await get_workspace_weekly_digest(db_session, digest.id, 2)


def test_resolve_weekly_digest_period_defaults_from_today():
    from app.services.weekly_digests import resolve_weekly_digest_period

    period = resolve_weekly_digest_period(None, None, today=date(2026, 3, 27))

    assert period.year == 2026
    assert period.week == 13


def test_resolve_previous_week_period_uses_previous_iso_week():
    from app.services.weekly_digests import resolve_previous_week_period

    period = resolve_previous_week_period(today=date(2026, 1, 4))

    assert period.year == 2025
    assert period.week == 52


@pytest.mark.asyncio
async def test_generate_workspace_weekly_digest_raises_when_provider_missing(monkeypatch, db_session):
    from app.services.weekly_digests import (
        WeeklyDigestProviderUnavailableError,
        generate_workspace_weekly_digest,
    )

    monkeypatch.setattr(
        "app.services.weekly_digests.get_default_llm_provider",
        MagicMock(side_effect=ValueError("provider missing")),
    )

    with pytest.raises(WeeklyDigestProviderUnavailableError) as exc:
        await generate_workspace_weekly_digest(db_session, 1, year=2026, week=12)

    assert str(exc.value) == "provider missing"


@pytest.mark.asyncio
async def test_generate_workspace_weekly_digest_delegates_to_digest_generator(monkeypatch, db_session):
    from app.llm.base import BaseLLMProvider
    from app.services.weekly_digests import generate_workspace_weekly_digest

    class DummyProvider(BaseLLMProvider):
        async def extract_learnings(self, pr_data):  # pragma: no cover - not used
            raise AssertionError("not called")

        async def generate_text(self, system_prompt, user_message):
            return json.dumps(
                {
                    "summary": "Weekly digest summary",
                    "repeated_issues": [],
                    "next_time_notes": [],
                }
            )

    provider = DummyProvider()
    delegate = AsyncMock(return_value="digest")
    monkeypatch.setattr("app.services.weekly_digests.get_default_llm_provider", MagicMock(return_value=provider))
    monkeypatch.setattr("app.services.digest_generator.generate_weekly_digest", delegate)

    result = await generate_workspace_weekly_digest(db_session, 7, year=2026, week=12)

    assert result == "digest"
    delegate.assert_awaited_once_with(2026, 12, 7, provider, db_session)


@pytest.mark.asyncio
async def test_fetch_learning_items_for_week_returns_week_scoped_items(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.digest_generator import fetch_learning_items_for_week

    workspace = Workspace(
        name="Alice Workspace",
        slug="alice-workspace",
        is_personal=True,
        created_at=datetime(2026, 3, 17, tzinfo=timezone.utc),
    )
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(
        workspace_id=workspace.id,
        github_id=1,
        full_name="alice/repo",
        name="repo",
        created_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
    )
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="pr",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/1",
        created_at=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )
    db_session.add(pr)
    await db_session.flush()

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=pr.id,
        schema_version="1.0",
        title="lesson",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="act",
        evidence="evidence",
        created_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )
    db_session.add(item)
    await db_session.commit()

    items = await fetch_learning_items_for_week(2026, 12, workspace.id, db_session)

    assert [row.id for row in items] == [item.id]
