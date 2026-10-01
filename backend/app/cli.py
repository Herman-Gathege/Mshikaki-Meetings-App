"""Operational commands: `python -m app.cli <command>`.

Kept deliberately small and dependency-free (argparse, no task runner). The
container entrypoint uses `wait-for-db`; the daily digest will use `send-digest`.
"""

from __future__ import annotations

import argparse
import sys
import time

from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db.session import get_engine
from app.logging_setup import configure_logging


def wait_for_db(timeout: int = 60, interval: float = 1.5) -> int:
    """Block until Postgres answers, or give up with a clear message."""
    from sqlalchemy import text

    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            print(f"Database is reachable (after {attempt} attempt(s)).")
            return 0
        except (SQLAlchemyError, OSError) as exc:
            if time.monotonic() >= deadline:
                print(
                    f"Database still unreachable after {timeout}s: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                return 1
            time.sleep(interval)


def seed() -> int:
    """Load game definitions, content packs, XP rules and achievements."""
    from app.db.session import get_session_factory
    from app.seeds import seed_all

    with get_session_factory()() as db:
        result = seed_all(db)

    for key, value in result.items():
        print(f"{key}: {value}")
    if result.get("content_dir_missing"):
        print("Warning: the content pack directory was not found; the library is empty.")
    return 0


def send_digest() -> int:
    """Placeholder until the daily digest lands in Phase 4 (P4-14)."""
    settings = get_settings()
    if not settings.digest_enabled or not settings.smtp_host:
        print("Digest is disabled. Set DIGEST_ENABLED=true and SMTP_HOST to enable it.")
        return 0
    print("Digest sending arrives in Phase 4.")
    return 0


def preflight() -> int:
    """The checklist to run before a real meeting."""
    import os
    import time

    from sqlalchemy import func, select, text

    from app.db.models import Achievement, ContentPack, GameDefinition, GameQuestion, XpRuleModel
    from app.db.session import get_session_factory
    from app.domain.preflight import backup_problem, config_problems, content_problems

    settings = get_settings()
    problems: list[str] = []
    notes: list[str] = []

    lines = [
        f"environment      {settings.app_env}",
        f"serving at       {settings.root_url}",
        f"sign-in emails   {', '.join(settings.email_domains) or 'any address (open)'}",
    ]
    problems.extend(config_problems(settings))

    try:
        with get_session_factory()() as db:

            def count(model) -> int:
                return int(db.execute(select(func.count()).select_from(model)).scalar_one())

            definitions = count(GameDefinition)
            packs = count(ContentPack)
            questions = count(GameQuestion)
            rules = count(XpRuleModel)
            achievements = count(Achievement)
            migration = db.execute(text("select version_num from alembic_version")).scalar_one()

        lines += [
            f"database         reachable, at migration {migration}",
            f"games            {definitions} definitions, {packs} packs, {questions} questions",
            f"bragging rights  {rules} XP rules, {achievements} achievements",
        ]
        problems.extend(
            content_problems(
                game_definitions=definitions,
                content_packs=packs,
                questions=questions,
                xp_rules=rules,
            )
        )
    except Exception as exc:  # noqa: BLE001 - this is a check, not a request path
        problems.append(f"Database check failed: {type(exc).__name__}: {exc}")

    # Backups live next to the compose file, mounted read-only at /app/backups in
    # the container, and ./backups from the repository root on a developer machine.
    backup_dir = os.environ.get("BACKUP_DIR") or os.path.join(os.getcwd(), "backups")
    newest: float | None = None
    if os.path.isdir(backup_dir):
        stamps = [
            os.path.getmtime(os.path.join(backup_dir, name))
            for name in os.listdir(backup_dir)
            if name.startswith("mshikaki-") and name.endswith(".sql.gz")
        ]
        if stamps:
            newest = (time.time() - max(stamps)) / 3600
    problem = backup_problem(newest)
    if problem:
        problems.append(problem)
    elif newest is not None:
        notes.append(f"newest backup is {newest:.0f} hours old")

    print("Mshikaki preflight")
    for line in lines:
        print(f"  {line}")
    for note in notes:
        print(f"  note: {note}")
    if problems:
        print("\nProblems to fix before the meeting:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nAll checks passed. Have a good meeting.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Mshikaki operations")
    sub = parser.add_subparsers(dest="command", required=True)

    wait = sub.add_parser("wait-for-db", help="Block until the database accepts connections")
    wait.add_argument("--timeout", type=int, default=60)

    sub.add_parser("seed", help="Load game definitions and content packs")
    sub.add_parser("send-digest", help="Send the daily digest email")
    sub.add_parser("preflight", help="Check the configuration, content and backups")

    args = parser.parse_args(argv)
    configure_logging(get_settings())

    if args.command == "wait-for-db":
        return wait_for_db(timeout=args.timeout)
    if args.command == "seed":
        return seed()
    if args.command == "send-digest":
        return send_digest()
    if args.command == "preflight":
        return preflight()

    parser.error(f"Unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
