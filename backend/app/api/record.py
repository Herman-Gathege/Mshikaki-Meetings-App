"""Reading the record: the team activity feed and search."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.db.models import Decision, Idea, Task
from app.deps import DbDep, require_capability
from app.domain.permissions import can
from app.services import activity as activity_service
from app.services import work

router = APIRouter(tags=["record"])


@router.get("/activity")
def team_activity(
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    session_id: uuid.UUID | None = None,
    limit: int = 50,
    context=require_capability("activity.view.team"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    rows = activity_service.for_team(
        db,
        team_id=context.team.id,
        limit=limit,
        actor_id=actor_id,
        target_type=target_type,
        session_id=session_id,
    )
    visible = can(context.actor, "activity.view.admin")
    return {
        "items": [activity_service.serialize(row, viewer_can_see_admin=visible) for row in rows]
    }


@router.get("/search")
def search(
    q: str,
    context=require_capability("search.use"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    term = f"%{q.strip()}%"
    if not q.strip():
        return {"ideas": [], "decisions": [], "tasks": []}

    ideas = db.execute(
        select(Idea)
        .where(
            Idea.team_id == context.team.id,
            Idea.deleted_at.is_(None),
            or_(Idea.title.ilike(term), Idea.description.ilike(term)),
        )
        .limit(20)
    ).scalars()
    decisions = db.execute(
        select(Decision)
        .where(
            Decision.team_id == context.team.id,
            Decision.deleted_at.is_(None),
            Decision.statement.ilike(term),
        )
        .limit(20)
    ).scalars()
    tasks = db.execute(
        select(Task)
        .where(
            Task.team_id == context.team.id,
            Task.deleted_at.is_(None),
            or_(Task.title.ilike(term), Task.description.ilike(term)),
        )
        .limit(20)
    ).scalars()

    return {
        "ideas": [work.idea_row(db, idea) for idea in ideas],
        "decisions": [work.decision_row(db, decision) for decision in decisions],
        "tasks": [work.task_row(db, task) for task in tasks],
    }
