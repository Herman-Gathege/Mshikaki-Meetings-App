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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Mshikaki operations")
    sub = parser.add_subparsers(dest="command", required=True)

    wait = sub.add_parser("wait-for-db", help="Block until the database accepts connections")
    wait.add_argument("--timeout", type=int, default=60)

    sub.add_parser("seed", help="Load game definitions and content packs")
    sub.add_parser("send-digest", help="Send the daily digest email")

    args = parser.parse_args(argv)
    configure_logging(get_settings())

    if args.command == "wait-for-db":
        return wait_for_db(timeout=args.timeout)
    if args.command == "seed":
        return seed()
    if args.command == "send-digest":
        return send_digest()

    parser.error(f"Unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
