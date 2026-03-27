import importlib.metadata as importlib_metadata
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

if "passlib.context" not in sys.modules:
    passlib_module = types.ModuleType("passlib")
    context_module = types.ModuleType("passlib.context")

    class _CryptContext:
        def __init__(self, *args, **kwargs):
            pass

        def hash(self, password: str) -> str:
            return f"hashed::{password}"

        def verify(self, plain: str, hashed: str) -> bool:
            return hashed == f"hashed::{plain}"

    context_module.CryptContext = _CryptContext
    passlib_module.context = context_module
    sys.modules["passlib"] = passlib_module
    sys.modules["passlib.context"] = context_module

if "email_validator" not in sys.modules:
    email_validator_module = types.ModuleType("email_validator")

    class EmailNotValidError(ValueError):
        pass

    class _ValidatedEmail:
        def __init__(self, email: str):
            self.email = email
            self.normalized = email
            self.local_part = email.split("@", 1)[0]

    def validate_email(email: str, *args, **kwargs):
        if "@" not in email:
            raise EmailNotValidError("invalid email")
        return _ValidatedEmail(email)

    email_validator_module.EmailNotValidError = EmailNotValidError
    email_validator_module.validate_email = validate_email
    sys.modules["email_validator"] = email_validator_module

_original_version = importlib_metadata.version


def _version_with_email_validator(name: str):
    if name == "email-validator":
        return "2.0.0"
    return _original_version(name)


importlib_metadata.version = _version_with_email_validator

from app.db.session import Base  # noqa: E402
from app.db import models as _models  # noqa: F401,E402
from app.llm.base import BaseLLMProvider  # noqa: E402
from app.schemas.llm_output import LLMOutputV1, LearningItem as LLMLearningItem  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_llm_output() -> LLMOutputV1:
    return LLMOutputV1(
        schema_version="1.0",
        source="github-owner/repo-42",
        summary="Test PR summary",
        learning_items=[
            LLMLearningItem(
                title="Add validation before persistence",
                detail="Validate request payloads before saving.",
                category="code_quality",
                confidence=0.9,
                action_for_next_time="Add validation checks in the request layer.",
                evidence="A review comment pointed out missing validation.",
            )
        ],
        repeated_issues=["missing validation"],
        next_time_notes=["add mypy to CI"],
    )


@pytest.fixture
def mock_llm_provider(sample_llm_output: LLMOutputV1):
    provider = MagicMock(spec=BaseLLMProvider)
    provider.extract_learnings = AsyncMock(return_value=sample_llm_output)
    provider.generate_text = AsyncMock(
        return_value='{"summary": "Weekly digest summary", "repeated_issues": [], "next_time_notes": []}'
    )
    return provider


@pytest.fixture
def sample_pr_data() -> dict:
    return {
        "pr_id": "github-owner/repo-42",
        "title": "Fix missing validation",
        "description": "Add validation before persistence.",
        "diff_summary": "5 files changed, +30 / -5",
        "review_comments": [
            {
                "id": "1",
                "author": "reviewer1",
                "body": "Please validate the payload before saving it.",
                "file": "app/utils.py",
                "line": 42,
                "diff_hunk": "@@ -40,3 +40,3 @@\n def helper(x):",
                "resolved": False,
            }
        ],
    }
