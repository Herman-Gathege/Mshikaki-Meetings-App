"""One logging configuration, used by the app factory and the CLI."""

from __future__ import annotations

import logging

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
