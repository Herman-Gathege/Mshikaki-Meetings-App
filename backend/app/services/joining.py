"""Joining by QR: scan, create an account, and land in the meeting.

There are no guests in Mshikaki. Scanning an invite makes you a real user with an
account, a team membership, and a place in the session you were invited to -- you
need that account to manage the session and everything it produces.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.db.models import AuthSession, Membership, SessionParticipant, Team, User
from app.db.models import Session as MeetingSession
from app.domain.enums import SessionStatus
from app.errors import AppError
from app.services import auth as auth_service
from app.services import identity
from app.services.activity import record_activity


def target_session(db: DbSession, *, team_id: uuid.UUID) -> MeetingSession | None:
    """Where a new joiner lands: the live meeting, else the next one planned."""
    return (
        db.execute(
            select(MeetingSession)
            .where(
                MeetingSession.team_id == team_id,
                MeetingSession.status.in_(
                    [
                        SessionStatus.ACTIVE.value,
                        SessionStatus.PAUSED.value,
                        SessionStatus.PLANNED.value,
                    ]
                ),
                MeetingSession.deleted_at.is_(None),
            )
            .order_by(
                MeetingSession.status.desc(),
                MeetingSession.scheduled_at.asc().nullslast(),
            )
        )
        .scalars()
        .first()
    )


def preview(db: DbSession, code: str) -> dict:
    """What the join page shows before anyone signs up."""
    invite = identity.find_invite(db, code)
    team = db.get(Team, invite.team_id)
    session = target_session(db, team_id=invite.team_id)
    return {
        "team_name": team.name if team else "a team",
        "role": invite.role,
        "email_domains": list(get_settings().email_domains),
        "session": (
            {
                "id": str(session.id),
                "title": session.title,
                "status": session.status,
                "scheduled_at": (
                    session.scheduled_at.isoformat() if session.scheduled_at else None
                ),
            }
            if session
            else None
        ),
    }


def join(
    db: DbSession,
    *,
    code: str,
    display_name: str,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[User, Membership, Team, MeetingSession | None, str]:
    settings = get_settings()
    if not identity.email_domain_ok(email, settings.email_domains):
        raise AppError(
            f"Please use your work email ({', '.join(settings.email_domains)}).",
            code="join.email_domain",
        )

    # The code is shared on a projector, so it is reusable and never consumed.
    invite = identity.find_invite(db, code)
    user, membership, team = auth_service.register(
        db,
        email=email,
        display_name=display_name,
        password=password,
        invite=invite,
    )

    session = target_session(db, team_id=team.id)
    if session is not None:
        already = db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session.id,
                SessionParticipant.user_id == user.id,
            )
        ).scalar_one_or_none()
        if already is None:
            db.add(
                SessionParticipant(
                    session_id=session.id,
                    user_id=user.id,
                    attended=True,
                    joined_at=datetime.now(timezone.utc),
                )
            )
            db.flush()
            record_activity(
                db,
                team_id=team.id,
                session_id=session.id,
                actor=auth_service.actor_for(user, team.id, membership.role),
                actor_name=user.display_name,
                verb="session.participant_joined",
                target_type="session",
                target_id=session.id,
                payload={"role": "participant", "name": user.display_name},
            )

    token = auth_service.start_auth_session(db, user=user, user_agent=user_agent, ip=ip)
    return user, membership, team, session, token


def current_session_for(db: DbSession, *, team_id: uuid.UUID) -> MeetingSession | None:
    return target_session(db, team_id=team_id)


__all__ = ["AuthSession", "current_session_for", "join", "preview", "target_session"]
