"""The preflight rules, without a database."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.config import Settings
from app.domain.preflight import backup_problem, config_problems, content_problems
from pydantic import ValidationError


def settings(**overrides) -> SimpleNamespace:
    """A plain stand-in for Settings.

    The real Settings refuses to exist with production defaults, which is the
    stronger guarantee and is tested separately below.
    """
    base = {
        "app_env": "development",
        "app_secret_key": "a" * 48,
        "root_url": "http://localhost:8080",
        "session_cookie_secure": False,
        "postgres_password": "a-real-password",
        "digest_enabled": False,
        "smtp_host": None,
        "email_domains": ("kbc.co.ke",),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_settings_refuse_to_start_in_production_with_default_secrets() -> None:
    """The stronger guarantee: the app will not boot like that at all."""
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            app_secret_key="change-me",
            postgres_password="change-me",
            _env_file=None,  # type: ignore[call-arg]
        )


def test_a_healthy_development_configuration_is_quiet() -> None:
    assert config_problems(settings()) == []


def test_production_demands_real_secrets() -> None:
    problems = config_problems(
        settings(app_env="production", app_secret_key="change-me", postgres_password="change-me")
    )
    assert any("APP_SECRET_KEY" in problem for problem in problems)
    assert any("POSTGRES_PASSWORD" in problem for problem in problems)


def test_a_secure_cookie_over_http_would_lock_everybody_out() -> None:
    problems = config_problems(
        settings(root_url="http://172.16.1.36:8090", session_cookie_secure=True)
    )
    assert any("nobody can sign in" in problem for problem in problems)


def test_https_without_a_secure_cookie_is_reported() -> None:
    problems = config_problems(
        settings(root_url="https://mshikaki.example", session_cookie_secure=False)
    )
    assert any("travel unencrypted" in problem for problem in problems)


def test_an_open_join_policy_is_reported() -> None:
    problems = config_problems(settings(email_domains=()))
    assert any("any email address" in problem for problem in problems)


def test_an_empty_library_is_reported() -> None:
    problems = content_problems(game_definitions=0, content_packs=0, questions=0, xp_rules=0)
    assert len(problems) == 4
    assert content_problems(game_definitions=8, content_packs=8, questions=129, xp_rules=11) == []


def test_backup_age() -> None:
    assert backup_problem(None) is not None
    assert backup_problem(3) is None
    assert backup_problem(72) is not None
