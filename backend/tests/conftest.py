"""Shared test fixtures.

Phase 0 keeps this deliberately small. The database fixture and factories arrive
with P1-22, when there are tables to create.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def settings() -> Settings:
    """Settings for tests: development mode, no dotenv, no external services.

    Init arguments take precedence over environment variables in pydantic-settings,
    so a developer's real .env cannot leak into a test run.
    """
    return Settings(
        app_env="development",
        app_secret_key="test-secret",
        postgres_user="test",
        postgres_password="test",
        postgres_db="test",
        postgres_host="127.0.0.1",
        postgres_port=5432,
        static_dir=Path("/nonexistent-static"),
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
