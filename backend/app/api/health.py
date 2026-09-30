"""Health endpoints.

`/api/health` is liveness: the process is up. It must never touch the database,
because a database blip should not make the container look dead.

`/api/health/ready` is readiness: the process can serve traffic, which requires
a working database. Compose and any future proxy should use this one.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.deps import get_db_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


def check_database(engine: Engine) -> None:
    """Raise if the database cannot answer a trivial query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@router.get("/health/ready")
def health_ready(
    response: Response,
    engine: Annotated[Engine, Depends(get_db_engine)],
) -> dict[str, str]:
    try:
        check_database(engine)
    except (SQLAlchemyError, OSError) as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "database": "unreachable",
            "reason": type(exc).__name__,
        }
    return {"status": "ok", "database": "ok"}
