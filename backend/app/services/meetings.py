"""Sessions, participants and the agenda - the meeting frame."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.db.models import (
    AgendaItem,
    Decision,
    GamePlay,
    Guest,
    Idea,
    Membership,
    SessionParticipant,
    Task,
    User,
)
from app.db.models import Session as MeetingSession
from app.domain import sessions as session_rules
from app.domain.enums import GamePlayStatus, ParticipantRole, SessionStatus, TaskStatus
from app.errors import AppError, NotFoundError
from app.services.activity import record_activity
from app.services.summary import store_snapshot


def get_session(db: DbSession, *, team_id: uuid.UUID, session_id: uuid.UUID) -> MeetingSession:
    """Team-scoped lookup. A session from another team is not-found, never forbidden."""
    session = db.execute(
        select(MeetingSession).where(
            MeetingSession.id == session_id,
            MeetingSession.team_id == team_id,
            MeetingSession.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if session is None:
        raise NotFoundError("That session does not exist.")
    return session


def create_session(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    team_name: str,
    actor,
    actor_name: str,
    title: str | None = None,
    scheduled_at: datetime | None = None,
    location: str | None = None,
    agenda: list[str] | None = None,
    facilitator_id: uuid.UUID | None = None,
) -> MeetingSession:
    if (
        db.execute(
            select(MeetingSession.id).where(
                MeetingSession.team_id == team_id,
                MeetingSession.status == SessionStatus.ACTIVE.value,
            )
        ).first()
        is not None
    ):
        raise AppError(
            "A session is already running. Close it before starting another.",
            code="session.already_active",
        )

    existing = list(
        db.execute(
            select(MeetingSession.sequence_no).where(MeetingSession.team_id == team_id)
        ).scalars()
    )
    sequence_no = session_rules.next_sequence_number(existing)

    session = MeetingSession(
        team_id=team_id,
        title=(title or "").strip() or session_rules.default_title(team_name, sequence_no),
        sequence_no=sequence_no,
        status=SessionStatus.PLANNED.value,
        scheduled_at=scheduled_at,
        location=location,
        facilitator_id=facilitator_id or actor.user_id,
        created_by=actor.user_id,
    )
    db.add(session)
    db.flush()

    if session.facilitator_id is not None:
        _add_participant_row(
            db,
            session=session,
            user_id=session.facilitator_id,
            role=ParticipantRole.FACILITATOR.value,
        )

    for index, line in enumerate(agenda or []):
        text = line.strip()
        if text:
            db.add(AgendaItem(session_id=session.id, position=index, title=text[:200]))
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="session.created",
        target_type="session",
        target_id=session.id,
        payload={
            "title": session.title,
            "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
        },
    )
    return session


def _add_participant_row(
    db: DbSession,
    *,
    session: MeetingSession,
    user_id: uuid.UUID | None = None,
    guest_id: uuid.UUID | None = None,
    role: str = ParticipantRole.PARTICIPANT.value,
) -> SessionParticipant:
    if user_id is not None:
        existing = db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session.id,
                SessionParticipant.user_id == user_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    row = SessionParticipant(
        session_id=session.id,
        user_id=user_id,
        guest_id=guest_id,
        role=role,
        attended=False,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def add_participant(
    db: DbSession,
    *,
    session: MeetingSession,
    actor,
    actor_name: str,
    user_id: uuid.UUID | None = None,
    guest_id: uuid.UUID | None = None,
    name: str | None = None,
    role: str = ParticipantRole.PARTICIPANT.value,
) -> SessionParticipant:
    if user_id is None and guest_id is None:
        raise AppError("A participant needs a person.", code="participant.invalid")

    if user_id is not None:
        member = db.execute(
            select(Membership).where(
                Membership.user_id == user_id, Membership.team_id == session.team_id
            )
        ).scalar_one_or_none()
        if member is None:
            raise AppError("That person is not in this team.", code="participant.not_member")

    row = _add_participant_row(db, session=session, user_id=user_id, guest_id=guest_id, role=role)
    display = name or _display_name(db, user_id=user_id, guest_id=guest_id)

    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="session.participant_joined",
        target_type="session",
        target_id=session.id,
        payload={"role": role, "name": display},
    )
    return row


def _display_name(db: DbSession, *, user_id: uuid.UUID | None, guest_id: uuid.UUID | None) -> str:
    if user_id is not None:
        user = db.get(User, user_id)
        return user.display_name if user else "Someone"
    if guest_id is not None:
        guest = db.get(Guest, guest_id)
        return guest.display_name if guest else "A guest"
    return "Someone"


def mark_attendance(
    db: DbSession,
    *,
    session: MeetingSession,
    participant_id: uuid.UUID,
    attended: bool,
    actor,
    actor_name: str,
) -> SessionParticipant:
    participant = db.get(SessionParticipant, participant_id)
    if participant is None or participant.session_id != session.id:
        raise NotFoundError("That participant is not in this session.")
    participant.attended = attended
    if attended and participant.joined_at is None:
        participant.joined_at = datetime.now(timezone.utc)
    db.flush()

    name = _display_name(db, user_id=participant.user_id, guest_id=participant.guest_id)
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="session.attendance_changed",
        target_type="session",
        target_id=session.id,
        payload={"name": name, "attended": "present" if attended else "absent"},
    )
    if attended and participant.user_id is not None:
        from app.services.bragging import award_for_event

        award_for_event(
            db,
            team_id=session.team_id,
            user_id=participant.user_id,
            subject_name=name,
            rule_key="attend_session",
            source_type="session",
            source_id=session.id,
            session_id=session.id,
            actor=actor,
            actor_name=actor_name,
        )
    return participant


def remove_participant(
    db: DbSession, *, session: MeetingSession, participant_id: uuid.UUID, actor, actor_name: str
) -> None:
    participant = db.get(SessionParticipant, participant_id)
    if participant is None or participant.session_id != session.id:
        raise NotFoundError("That participant is not in this session.")
    name = _display_name(db, user_id=participant.user_id, guest_id=participant.guest_id)
    db.delete(participant)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="session.participant_removed",
        target_type="session",
        target_id=session.id,
        payload={"name": name},
    )


# --- lifecycle -----------------------------------------------------------------


def _lifecycle(
    db: DbSession,
    *,
    session: MeetingSession,
    target: str,
    actor,
    actor_name: str,
    reason: str | None = None,
) -> MeetingSession:
    session_rules.ensure_transition(session.status, target)
    previous = session.status
    session.status = target
    now = datetime.now(timezone.utc)

    if target == SessionStatus.ACTIVE.value:
        session.started_at = session.started_at or now
        session.ended_at = None
        verb = (
            "session.resumed"
            if previous == SessionStatus.PAUSED.value
            else (
                "session.reopened"
                if previous == SessionStatus.COMPLETED.value
                else "session.started"
            )
        )
        payload = {"reason": reason} if verb == "session.reopened" else {}
    elif target == SessionStatus.PAUSED.value:
        verb, payload = "session.paused", {}
    elif target == SessionStatus.CANCELLED.value:
        verb, payload = "session.updated", {"title": session.title, "note": "cancelled"}
    else:
        verb, payload = "session.updated", {"title": session.title}

    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb=verb,
        target_type="session",
        target_id=session.id,
        payload=payload,
    )
    return session


def start_session(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str
) -> MeetingSession:
    if session.status == SessionStatus.PLANNED.value:
        clash = db.execute(
            select(MeetingSession.id).where(
                MeetingSession.team_id == session.team_id,
                MeetingSession.status == SessionStatus.ACTIVE.value,
                MeetingSession.id != session.id,
            )
        ).first()
        if clash is not None:
            raise AppError("Another session is already running.", code="session.already_active")
    return _lifecycle(
        db, session=session, target=SessionStatus.ACTIVE.value, actor=actor, actor_name=actor_name
    )


def pause_session(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str
) -> MeetingSession:
    return _lifecycle(
        db, session=session, target=SessionStatus.PAUSED.value, actor=actor, actor_name=actor_name
    )


def resume_session(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str
) -> MeetingSession:
    return _lifecycle(
        db, session=session, target=SessionStatus.ACTIVE.value, actor=actor, actor_name=actor_name
    )


def reopen_session(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str, reason: str
) -> MeetingSession:
    """A closed meeting continued tomorrow. Audited, and the summary goes stale."""
    return _lifecycle(
        db,
        session=session,
        target=SessionStatus.ACTIVE.value,
        actor=actor,
        actor_name=actor_name,
        reason=reason,
    )


def close_session(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str, regenerate: bool = False
) -> MeetingSession:
    if not regenerate:
        session_rules.ensure_transition(session.status, SessionStatus.COMPLETED.value)

    session.status = SessionStatus.COMPLETED.value
    session.ended_at = datetime.now(timezone.utc)
    db.flush()

    counts = session_counts(db, session.id)
    store_snapshot(db, session=session, actor=actor, actor_name=actor_name, regenerate=regenerate)

    if not regenerate:
        record_activity(
            db,
            team_id=session.team_id,
            session_id=session.id,
            actor=actor,
            actor_name=actor_name,
            verb="session.closed",
            target_type="session",
            target_id=session.id,
            payload=counts,
        )
    return session


def session_counts(db: DbSession, session_id: uuid.UUID) -> dict[str, int]:
    def count(model, *conditions, deleted: bool = False) -> int:
        query = select(func.count()).select_from(model).where(*conditions)
        if deleted and hasattr(model, "deleted_at"):
            query = query.where(model.deleted_at.is_(None))
        return int(db.execute(query).scalar_one())

    return {
        "ideas": count(Idea, Idea.session_id == session_id, deleted=True),
        "decisions": count(Decision, Decision.session_id == session_id, deleted=True),
        "tasks": count(Task, Task.session_id == session_id, deleted=True),
        "games": count(GamePlay, GamePlay.session_id == session_id),
    }


def session_detail(db: DbSession, session: MeetingSession) -> dict:
    counts = session_counts(db, session.id)
    tasks = list(
        db.execute(
            select(Task).where(Task.session_id == session.id, Task.deleted_at.is_(None))
        ).scalars()
    )
    ideas = list(
        db.execute(
            select(Idea)
            .where(Idea.session_id == session.id, Idea.deleted_at.is_(None))
            .order_by(Idea.created_at)
        ).scalars()
    )
    decisions = list(
        db.execute(
            select(Decision)
            .where(Decision.session_id == session.id, Decision.deleted_at.is_(None))
            .order_by(Decision.decided_at)
        ).scalars()
    )
    plays = list(
        db.execute(
            select(GamePlay).where(GamePlay.session_id == session.id).order_by(GamePlay.created_at)
        ).scalars()
    )
    facilitator = db.get(User, session.facilitator_id) if session.facilitator_id else None

    return {
        "id": str(session.id),
        "title": session.title,
        "sequence_no": session.sequence_no,
        "status": session.status,
        "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "location": session.location,
        "facilitator": (
            {"id": str(facilitator.id), "name": facilitator.display_name} if facilitator else None
        ),
        "counts": counts,
        "tasks_open": len(
            [
                t
                for t in tasks
                if t.status not in {TaskStatus.DONE.value, TaskStatus.CANCELLED.value}
            ]
        ),
        "has_summary": session.summary_snapshot is not None,
        "summary_generated_at": (
            session.summary_generated_at.isoformat() if session.summary_generated_at else None
        ),
        "agenda": [
            {
                "id": str(item.id),
                "position": item.position,
                "title": item.title,
                "covered": item.covered_at is not None,
                "timebox_minutes": item.timebox_minutes,
            }
            for item in session.agenda_items
        ],
        "ideas": [
            {
                "id": str(idea.id),
                "title": idea.title,
                "status": idea.status,
                "author": idea.author_name,
            }
            for idea in ideas
        ],
        "decisions": [
            {
                "id": str(decision.id),
                "statement": decision.statement,
                "recorded_by": decision.decided_by_name,
            }
            for decision in decisions
        ],
        "games": [
            {"id": str(play.id), "key": play.game_definition_key, "status": play.status}
            for play in plays
        ],
    }


def list_sessions(db: DbSession, *, team_id: uuid.UUID, limit: int = 50) -> list[dict]:
    sessions = list(
        db.execute(
            select(MeetingSession)
            .where(MeetingSession.team_id == team_id, MeetingSession.deleted_at.is_(None))
            .order_by(
                MeetingSession.scheduled_at.desc().nullslast(), MeetingSession.created_at.desc()
            )
            .limit(min(limit, 100))
        ).scalars()
    )
    rows = []
    for session in sessions:
        facilitator = db.get(User, session.facilitator_id) if session.facilitator_id else None
        rows.append(
            {
                "id": str(session.id),
                "title": session.title,
                "sequence_no": session.sequence_no,
                "status": session.status,
                "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "location": session.location,
                "facilitator": facilitator.display_name if facilitator else None,
                "counts": session_counts(db, session.id),
            }
        )
    return rows


def active_session(db: DbSession, team_id: uuid.UUID) -> MeetingSession | None:
    return db.execute(
        select(MeetingSession).where(
            MeetingSession.team_id == team_id,
            MeetingSession.status == SessionStatus.ACTIVE.value,
            MeetingSession.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def upcoming_session(db: DbSession, team_id: uuid.UUID) -> MeetingSession | None:
    return (
        db.execute(
            select(MeetingSession)
            .where(
                MeetingSession.team_id == team_id,
                MeetingSession.status == SessionStatus.PLANNED.value,
                MeetingSession.deleted_at.is_(None),
            )
            .order_by(
                MeetingSession.scheduled_at.asc().nullslast(), MeetingSession.created_at.asc()
            )
        )
        .scalars()
        .first()
    )


def participants(db: DbSession, session: MeetingSession) -> list[dict]:
    rows = []
    for participant in session.participants:
        name = _display_name(db, user_id=participant.user_id, guest_id=participant.guest_id)
        rows.append(
            {
                "id": str(participant.id),
                "user_id": str(participant.user_id) if participant.user_id else None,
                "guest_id": str(participant.guest_id) if participant.guest_id else None,
                "name": name,
                "role": participant.role,
                "attended": participant.attended,
            }
        )
    return sorted(rows, key=lambda row: (not row["attended"], row["name"]))


def mark_game_finished(db: DbSession, *, session: MeetingSession, play_id: uuid.UUID) -> None:
    play = db.get(GamePlay, play_id)
    if play is None or play.session_id != session.id:
        raise NotFoundError("That game play is not in this session.")
    play.status = GamePlayStatus.FINISHED.value
    db.flush()


# --- agenda --------------------------------------------------------------------


def add_agenda_item(
    db: DbSession,
    *,
    session: MeetingSession,
    title: str,
    actor,
    actor_name: str,
    timebox_minutes: int | None = None,
) -> AgendaItem:
    position = len(session.agenda_items)
    item = AgendaItem(
        session_id=session.id,
        position=position,
        title=title.strip()[:200],
        timebox_minutes=timebox_minutes,
    )
    db.add(item)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="agenda.added",
        target_type="session",
        target_id=session.id,
        payload={"title": item.title},
    )
    return item


def cover_agenda_item(
    db: DbSession, *, session: MeetingSession, item_id: uuid.UUID, actor, actor_name: str
) -> AgendaItem:
    item = db.get(AgendaItem, item_id)
    if item is None or item.session_id != session.id:
        raise NotFoundError("That agenda item does not exist.")
    item.covered_at = datetime.now(timezone.utc)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="agenda.covered",
        target_type="session",
        target_id=session.id,
        payload={"title": item.title},
    )
    return item


def remove_agenda_item(
    db: DbSession, *, session: MeetingSession, item_id: uuid.UUID, actor, actor_name: str
) -> None:
    item = db.get(AgendaItem, item_id)
    if item is None or item.session_id != session.id:
        raise NotFoundError("That agenda item does not exist.")
    title = item.title
    db.delete(item)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="agenda.removed",
        target_type="session",
        target_id=session.id,
        payload={"title": title},
    )
