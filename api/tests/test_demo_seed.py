import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.models import LearningItem, PullRequest, Repository, User, WeeklyDigest, Workspace
from app.services.demo_seed import seed_demo_data


@pytest.mark.asyncio
async def test_seed_demo_data_is_idempotent(db_session):
    first = await seed_demo_data(
        db_session,
        email="demo-seed@example.com",
        password="demo12345",
        year=2026,
        week=13,
    )
    second = await seed_demo_data(
        db_session,
        email="demo-seed@example.com",
        password="demo12345",
        year=2026,
        week=13,
    )

    assert first.email == second.email
    assert first.workspace_id == second.workspace_id

    assert await db_session.scalar(select(func.count()).select_from(User)) == 1
    assert await db_session.scalar(select(func.count()).select_from(Workspace)) == 1
    assert await db_session.scalar(select(func.count()).select_from(Repository)) == 2
    assert await db_session.scalar(select(func.count()).select_from(PullRequest)) == 2
    assert await db_session.scalar(select(func.count()).select_from(LearningItem)) == 4
    assert await db_session.scalar(select(func.count()).select_from(WeeklyDigest)) == 1
