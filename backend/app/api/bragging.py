"""Bragging rights: XP, achievements and the leaderboard."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, require_capability
from app.services import bragging, meetings

router = APIRouter(tags=["bragging"])


@router.get("/leaderboard")
def leaderboard(
    scope: str = "season",
    session_id: uuid.UUID | None = None,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    standings = bragging.leaderboard(
        db, team_id=context.team.id, scope=scope, session_id=session_id
    )
    return {
        "scope": scope,
        "items": standings,
        "disclaimer": "For fun. Not a performance measure.",
    }


@router.get("/me/points")
def my_points(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    return bragging.my_points(db, team_id=context.team.id, user_id=context.user.id)


@router.get("/achievements")
def achievements(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    return bragging.achievements_overview(db, team_id=context.team.id, user_id=context.user.id)


@router.post("/achievements/sync")
def sync_achievements(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    newly = bragging.sync_achievements(db, team_id=context.team.id, user_id=context.user.id)
    return {"newly_earned": newly}


@router.get("/metrics")
def metrics(context=require_capability("metrics.view"), db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    return bragging.team_metrics(db, team_id=context.team.id)


@router.get("/sessions/{session_id}/leaderboard")
def session_leaderboard(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    standings = bragging.leaderboard(
        db, team_id=context.team.id, scope="session", session_id=session.id
    )
    return {
        "scope": "session",
        "items": standings,
        "disclaimer": "For fun. Not a performance measure.",
    }
