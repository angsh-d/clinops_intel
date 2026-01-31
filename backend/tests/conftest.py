"""Shared test fixtures: real PostgreSQL with SAVEPOINT rollback, mock LLM client."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.dependencies import get_db
from backend.main import app
from backend.llm.client import LLMClient, LLMResponse


# ── Database fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_engine():
    """One engine for the entire test session."""
    settings = get_settings()
    eng = create_engine(settings.clinops_db_url, echo=False, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Per-test session with SAVEPOINT rollback — no data leaks between tests.

    Uses SQLAlchemy 2.0+ join_transaction_mode="create_savepoint" which
    automatically wraps every session.commit() in a SAVEPOINT so the outer
    transaction can be rolled back after each test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient with get_db overridden to use the rollback session."""
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


# ── Mock LLM ─────────────────────────────────────────────────────────────────

class MockLLMClient(LLMClient):
    """Returns canned JSON responses keyed by prompt substring."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.call_log: list[dict] = []

    def _find_response(self, prompt: str) -> str:
        for key, value in self.responses.items():
            if key in prompt:
                return value
        return '{"result": "mock"}'

    async def generate(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        self.call_log.append({"method": "generate", "prompt": prompt, "system": system})
        return LLMResponse(text=self._find_response(prompt), model="mock", usage={})

    async def generate_structured(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        self.call_log.append({"method": "generate_structured", "prompt": prompt, "system": system})
        return LLMResponse(text=self._find_response(prompt), model="mock", usage={})


@pytest.fixture()
def mock_llm():
    """Yield a MockLLMClient instance."""
    return MockLLMClient()
