"""Fixtures for database-backed tests.

These run against the database in DATABASE_URL. They skip, rather than fail, when
no database is reachable, so `make check` still works on a fresh machine - but CI
and any rehearsal must run them, because they are the tests that protect the
product's promises.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
import pytest_asyncio  # noqa: F401  (registers the async fixtures below)
from app.config import get_settings
from app.db.session import get_engine, reset_engine
from app.deps import CSRF_HEADER
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


def database_available() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def app():
    settings = get_settings()
    return create_app(settings)


@pytest_asyncio.fixture
async def client(app) -> Iterator[AsyncClient]:
    transport = ASGITransport(app=app)
    headers = {CSRF_HEADER: "1"}
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as async_client:
        yield async_client


@pytest.fixture
def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


def pytest_collection_modifyitems(config, items):
    if database_available():
        return
    skip = pytest.mark.skip(reason="No database reachable at DATABASE_URL")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _reset_engine_between_tests():
    reset_engine()
    yield
    reset_engine()
