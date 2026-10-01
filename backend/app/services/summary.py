"""Building and storing the session summary.

The summary is a frozen snapshot taken when a session closes. Regenerating is
explicit and audited: the previous snapshot is replaced, not silently edited, and
the activity trail keeps both facts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models import (
    Blocker,
    ContentPack,
    Decision,
    GameDefinition,
    GamePlay,
    GameScore,
    Guest,
    Idea,
    Task,
    User,
    XpEvent,
)
from app.db.models import Session as MeetingSession
from app.domain import summary as summary_domain
from app.domain.enums import IdeaStatus, TaskStatus
from app.services.activity import record_activity


def _people(db: DbSession, session: MeetingSession) -> list[dict]:
    rows = []
    for participant in session.participants:
        name = "Someone"
        if participant.user_id is not None:
            user = db.get(User, participant.user_id)
            name = user.display_name if user else "Someone"
        elif participant.guest_id is not None:
            guest = db.get(Guest, participant.guest_id)
            name = guest.display_name if guest else "A guest"
        rows.append(
            {
                "name": name,
                "role": participant.role,
                # Being added to a session means you were in it; the facilitator
                # toggles attendance off for no-shows rather than on for everyone.
                "attended": participant.attended or participant.joined_at is not None,
                "user_id": str(participant.user_id) if participant.user_id else None,
                "guest_id": str(participant.guest_id) if participant.guest_id else None,
            }
        )
    return rows


def _games(db: DbSession, session_id) -> list[dict]:
    plays = list(db.execute(select(GamePlay).where(GamePlay.session_id == session_id)).scalars())
    rows: list[dict] = []
    for play in plays:
        definition = db.execute(
            select(GameDefinition).where(GameDefinition.key == play.game_definition_key)
        ).scalar_one_or_none()
        pack = db.get(ContentPack, play.content_pack_id) if play.content_pack_id else None
        scores = list(
            db.execute(
                select(GameScore)
                .where(GameScore.game_play_id == play.id)
                .order_by(GameScore.points.desc())
            ).scalars()
        )
        rows.append(
            {
                "name": definition.name if definition else play.game_definition_key,
                "family": definition.family if definition else "prompt_deck",
                "pack": pack.title if pack else None,
                "winner": scores[0].player_name if scores else None,
                "standings": [
                    {"name": score.player_name, "points": score.points} for score in scores
                ],
                "status": play.status,
            }
        )
    return rows


def _tasks(db: DbSession, session_id) -> list[Task]:
    return list(
        db.execute(
            select(Task).where(Task.session_id == session_id, Task.deleted_at.is_(None))
        ).scalars()
    )


def _task_rows(db: DbSession, tasks: list[Task]) -> list[dict]:
    rows = []
    for task in tasks:
        owner = db.get(User, task.owner_id) if task.owner_id else None
        rows.append(
            {
                "id": str(task.id),
                "title": task.title,
                "owner": owner.display_name if owner else None,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
        )
    return rows


def build_snapshot(db: DbSession, session: MeetingSession) -> dict:
    participants = _people(db, session)

    ideas = list(
        db.execute(
            select(Idea)
            .where(Idea.session_id == session.id, Idea.deleted_at.is_(None))
            .order_by(Idea.created_at)
        ).scalars()
    )
    idea_rows = [
        {
            "id": str(idea.id),
            "title": idea.title,
            "author": idea.author_name,
            "status": idea.status,
            "description": idea.description,
        }
        for idea in ideas
    ]

    decisions = list(
        db.execute(
            select(Decision)
            .where(Decision.session_id == session.id, Decision.deleted_at.is_(None))
            .order_by(Decision.decided_at)
        ).scalars()
    )
    decision_rows = [
        {
            "id": str(decision.id),
            "statement": decision.statement,
            "recorded_by": decision.decided_by_name,
            "rationale": decision.rationale,
        }
        for decision in decisions
    ]

    tasks = _tasks(db, session.id)
    created = _task_rows(db, tasks)
    completed = _task_rows(db, [t for t in tasks if t.status == TaskStatus.DONE.value])
    reopened = _task_rows(
        db,
        [t for t in tasks if t.completed_at is None and t.status == TaskStatus.IN_PROGRESS.value],
    )

    blockers = list(
        db.execute(
            select(Blocker).where(Blocker.task_id.in_([t.id for t in tasks]) if tasks else False)
        ).scalars()
    )
    task_titles = {t.id: t.title for t in tasks}
    raised = [
        {
            "title": task_titles.get(b.task_id, "a task"),
            "reason": b.reason,
            "raised_by": b.raised_by_name,
        }
        for b in blockers
        if b.resolved_at is None
    ]
    resolved = [
        {
            "title": task_titles.get(b.task_id, "a task"),
            "resolution": b.resolution,
            "resolved_by": b.resolved_by_name,
        }
        for b in blockers
        if b.resolved_at is not None
    ]

    xp_events = list(db.execute(select(XpEvent).where(XpEvent.session_id == session.id)).scalars())
    awards = [
        {"name": event.subject_name, "amount": event.amount, "reason": event.reason_key}
        for event in xp_events
    ]

    facilitator = db.get(User, session.facilitator_id) if session.facilitator_id else None

    return summary_domain.build_summary(
        session={
            "title": session.title,
            "sequence_no": session.sequence_no,
            "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "facilitator_name": facilitator.display_name if facilitator else None,
            "location": session.location,
        },
        participants=participants,
        games=_games(db, session.id),
        ideas=idea_rows,
        decisions=decision_rows,
        tasks_created=created,
        tasks_completed=completed,
        tasks_reopened=reopened,
        blockers_raised=raised,
        blockers_resolved=resolved,
        xp_awards=awards,
        agenda=[
            {"title": item.title, "covered": item.covered_at is not None}
            for item in session.agenda_items
        ],
        generated_at=datetime.now(timezone.utc),
    )


def store_snapshot(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str, regenerate: bool = False
) -> dict:
    snapshot = build_snapshot(db, session)
    session.summary_snapshot = snapshot
    session.summary_generated_at = datetime.now(timezone.utc)
    db.flush()

    if regenerate:
        record_activity(
            db,
            team_id=session.team_id,
            session_id=session.id,
            actor=actor,
            actor_name=actor_name,
            verb="session.updated",
            target_type="session",
            target_id=session.id,
            payload={"title": session.title, "note": "summary regenerated"},
        )
    return snapshot


def text_export(snapshot: dict) -> str:
    return summary_domain.render_text(snapshot)


def idea_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status", IdeaStatus.NEW.value))
        counts[status] = counts.get(status, 0) + 1
    return counts
