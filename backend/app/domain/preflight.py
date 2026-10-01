"""Checks to run before a real meeting.

Pure functions on settings and plain facts, so the rules are testable without a
database. `app.cli preflight` gathers the facts and prints the result.

The point is to catch, in a quiet moment, the configuration mistakes that would
otherwise surface in a room with twenty people watching: a login that cannot work
over the scheme in use, an empty game library, a backup nobody has taken.
"""

from __future__ import annotations

from typing import Any


def config_problems(settings: Any) -> list[str]:
    """Things that will bite in production but not in development."""
    problems: list[str] = []

    if settings.app_env == "production":
        if settings.app_secret_key.startswith("change-me"):
            problems.append(
                "APP_SECRET_KEY still has its default value. Generate one before deploying."
            )
        if settings.postgres_password == "change-me":
            problems.append("POSTGRES_PASSWORD still has its default value.")
        if len(settings.app_secret_key) < 32:
            problems.append("APP_SECRET_KEY is shorter than 32 characters.")

    secure = bool(settings.session_cookie_secure)
    https = settings.root_url.startswith("https://")

    if secure and not https:
        problems.append(
            "SESSION_COOKIE_SECURE is true but ROOT_URL is http, so the browser will "
            "refuse the cookie and nobody can sign in."
        )
    if https and not secure:
        problems.append(
            "ROOT_URL is https but SESSION_COOKIE_SECURE is false. The session cookie "
            "would travel unencrypted. Set it to true."
        )
    if not settings.root_url.startswith(("http://", "https://")):
        problems.append("ROOT_URL must start with http:// or https://.")

    if settings.digest_enabled and not settings.smtp_host:
        problems.append("DIGEST_ENABLED is true but SMTP_HOST is empty, so no digest sends.")

    if not settings.email_domains:
        problems.append(
            "ALLOWED_EMAIL_DOMAINS is empty, so anybody with any email address can join "
            "by scanning the code."
        )

    return problems


def content_problems(
    *, game_definitions: int, content_packs: int, questions: int, xp_rules: int
) -> list[str]:
    """An empty library is a meeting where nobody can play."""
    problems: list[str] = []
    if game_definitions == 0:
        problems.append("No game definitions. Run `python -m app.cli seed`.")
    if content_packs == 0:
        problems.append("No content packs. Run `python -m app.cli seed`.")
    if questions == 0:
        problems.append("No game questions, so every quiz will be empty.")
    if xp_rules == 0:
        problems.append("No XP rules, so the leaderboard will stay empty.")
    return problems


def backup_problem(age_hours: float | None) -> str | None:
    """A backup nobody has taken is not a backup."""
    if age_hours is None:
        return "No backup found in backups/. Run ./scripts/backup.sh."
    if age_hours > 48:
        return f"The newest backup is {age_hours:.0f} hours old. Check the backup cron."
    return None
