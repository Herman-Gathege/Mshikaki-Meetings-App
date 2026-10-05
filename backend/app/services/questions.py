"""Questions the room writes during a meeting.

The team's game library is content that ships with the product or that a team
curates. This is the other thing: somebody in the room says "ask them what the
old studio clock was for", the facilitator accepts it, and the next round plays
it. Nothing here invents a second game engine: accepted questions are gathered
into a content pack the existing engine already knows how to play.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models import ContentPack, GameQuestion, SessionQuestion
from app.db.models import Session as MeetingSession
from app.errors import AppError, NotFoundError
from app.services.activity import record_activity

STATUSES: tuple[str, ...] = ("suggested", "accepted", "used", "rejected")


def question_row(question: SessionQuestion) -> dict:
    return {
        "id": str(question.id),
        "prompt": question.prompt,
        "choices": question.choices or [],
        "answer": question.answer,
        "status": question.status,
        "author": question.author_name,
        "agenda_item_id": str(question.agenda_item_id) if question.agenda_item_id else None,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
    }


def _question(
    db: DbSession, *, session: MeetingSession, question_id: uuid.UUID
) -> SessionQuestion:
    question = db.get(SessionQuestion, question_id)
    if question is None or question.session_id != session.id or question.deleted_at is not None:
        raise NotFoundError("That question does not exist.")
    return question


def list_questions(db: DbSession, *, session: MeetingSession) -> list[dict]:
    rows = (
        db.execute(
            select(SessionQuestion)
            .where(
                SessionQuestion.session_id == session.id,
                SessionQuestion.deleted_at.is_(None),
            )
            .order_by(SessionQuestion.created_at)
        )
        .scalars()
        .all()
    )
    return [question_row(row) for row in rows]


def suggest_question(
    db: DbSession,
    *,
    session: MeetingSession,
    prompt: str,
    choices: list[str] | None,
    answer: str | None,
    agenda_item_id: uuid.UUID | None,
    actor,
    actor_name: str,
) -> SessionQuestion:
    """Anybody in the room may put a question on the table."""
    cleaned = [str(choice).strip() for choice in (choices or []) if str(choice).strip()]
    question = SessionQuestion(
        team_id=session.team_id,
        session_id=session.id,
        agenda_item_id=agenda_item_id,
        author_id=actor.user_id,
        author_name=actor_name,
        prompt=prompt.strip()[:500],
        choices=cleaned or None,
        answer=(answer or "").strip() or None,
        status="suggested",
    )
    db.add(question)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="question.suggested",
        target_type="session_question",
        target_id=question.id,
        payload={"prompt": question.prompt[:120]},
    )
    return question


def update_question(
    db: DbSession,
    *,
    session: MeetingSession,
    question_id: uuid.UUID,
    actor,
    actor_name: str,
    prompt: str | None = None,
    choices: list[str] | None = None,
    answer: str | None = None,
    status: str | None = None,
) -> SessionQuestion:
    question = _question(db, session=session, question_id=question_id)
    changes: list[str] = []
    if prompt is not None and prompt.strip() and prompt.strip() != question.prompt:
        question.prompt = prompt.strip()[:500]
        changes.append("prompt")
    if choices is not None:
        cleaned = [str(choice).strip() for choice in choices if str(choice).strip()]
        question.choices = cleaned or None
        changes.append("choices")
    if answer is not None:
        question.answer = answer.strip() or None
        changes.append("answer")
    if status is not None and status != question.status:
        if status not in STATUSES:
            raise AppError("That is not a question state.", code="question.bad_status")
        question.status = status
        changes.append("status")
    db.flush()
    if changes:
        record_activity(
            db,
            team_id=session.team_id,
            session_id=session.id,
            actor=actor,
            actor_name=actor_name,
            verb="question.updated",
            target_type="session_question",
            target_id=question.id,
            payload={"prompt": question.prompt[:120], "changes": ", ".join(changes)},
        )
    return question


def remove_question(
    db: DbSession,
    *,
    session: MeetingSession,
    question_id: uuid.UUID,
    actor,
    actor_name: str,
) -> None:
    question = _question(db, session=session, question_id=question_id)
    question.deleted_at = datetime.now(timezone.utc)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="question.removed",
        target_type="session_question",
        target_id=question.id,
        payload={"prompt": question.prompt[:120]},
    )


def pack_for_session(
    db: DbSession, *, session: MeetingSession, actor, actor_name: str
) -> ContentPack:
    """Gather this meeting's questions into a pack the game engine can play.

    Created once and updated on every call, so a question added late is in the
    next game without the facilitator doing anything.
    """
    asked = [
        row
        for row in db.execute(
            select(SessionQuestion)
            .where(
                SessionQuestion.session_id == session.id,
                SessionQuestion.deleted_at.is_(None),
                SessionQuestion.status.in_(["suggested", "accepted"]),
            )
            .order_by(SessionQuestion.created_at)
        ).scalars()
    ]
    if not asked:
        raise AppError(
            "The room has not written any questions yet.",
            code="question.none",
        )

    key = f"session-{session.id}"
    pack = db.execute(select(ContentPack).where(ContentPack.key == key)).scalar_one_or_none()
    if pack is None:
        pack = ContentPack(
            game_definition_key="trivia-general",
            key=key,
            title=f"{session.title} questions",
            description="Written by the room during the meeting.",
            license="Original content, created in Mshikaki",
            attribution=actor_name,
            is_seed=False,
            created_by=actor.user_id,
        )
        db.add(pack)
        db.flush()

    existing = {row.prompt: row for row in pack.questions}
    for index, question in enumerate(asked):
        row = existing.get(question.prompt)
        if row is None:
            row = GameQuestion(content_pack_id=pack.id, position=index, prompt=question.prompt)
            db.add(row)
        row.position = index
        row.choices = question.choices
        row.answer = question.answer
        row.category = "from the room"
    db.flush()
    return pack
