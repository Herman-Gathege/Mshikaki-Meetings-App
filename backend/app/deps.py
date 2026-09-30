"""Shared FastAPI dependencies.

Phase 0 has only the database handle and the settings accessor. Current-user and
`require_capability` dependencies arrive in Phase 1 and will live here too, so
every router has one obvious place to look for them.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings
from app.db.session import get_engine


def get_db_engine() -> Engine:
    return get_engine()


SettingsDep = Annotated[Settings, Depends(get_settings)]
