"""The Today screen: one request, everything a person needs to start."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep
from app.services import activity as activity_service
from app.services import bragging, meetings, work

router = APIRouter(tags=["today"])


@router.get("/today")
def today(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    team_id = context.team.id

    active = meetings.active_session(db, team_id)
    upcoming = meetings.upcoming_session(db, team_id)
    session = active or upcoming

    my_open = [
        task
        for task in work.my_tasks(db, team_id=team_id, user_id=context.user.id)
        if task.status not in {"done", "cancelled"}
    ]
    blockers = work.list_blockers(db, team_id=team_id, open_only=True)
    recent = activity_service.for_team(db, team_id=team_id, limit=8)
    standings = bragging.leaderboard(db, team_id=team_id, scope="season")[:5]
    points = bragging.my_points(db, team_id=team_id, user_id=context.user.id)

    return {
        "session": (
            {
                "id": str(session.id),
                "title": session.title,
                "status": session.status,
                "scheduled_at": (
                    session.scheduled_at.isoformat() if session.scheduled_at else None
                ),
                "sequence_no": session.sequence_no,
            }
            if session
            else None
        ),
        "my_tasks": [work.task_row(db, task) for task in my_open[:8]],
        "my_open_count": len(my_open),
        "blockers": [work.blocker_row(db, blocker) for blocker in blockers[:5]],
        "activity": [activity_service.serialize(row) for row in recent],
        "leaderboard": standings,
        "my_points": points,
    }
