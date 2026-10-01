"""Shared FastAPI dependencies: the database handle, the caller, and access checks.

Everything a router needs to answer "who is asking, and may they?" lives here, so
there is exactly one place to audit.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Cookie, Depends, status
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.db.models import AuthSession, Membership, Team, User
from app.db.session import get_engine, get_session_factory
from app.domain.enums import MembershipStatus, TeamRole
from app.domain.permissions import Actor, Resource, can
from app.errors import AppError, PermissionDeniedError

SESSION_COOKIE = "mshikaki_session"
# A custom header required on every mutation. Browsers will not send a custom
# header cross-site without a CORS preflight, which we never allow in production.
CSRF_HEADER = "x-mshikaki-request"


class NotAuthenticatedError(AppError):
    code = "auth.required"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Sign in to continue."


def get_db() -> Iterator[DbSession]:
    """One transaction per request: commit on success, roll back on any exception.

    Routers therefore never call commit themselves, and a request that fails
    halfway cannot leave a partial change or a dangling activity row.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_engine() -> Engine:
    return get_engine()


DbDep = Depends(get_db)


@dataclass
class RequestContext:
    """Who is calling, and which team they are acting in."""

    user: User
    membership: Membership
    team: Team
    auth_session: AuthSession

    @property
    def actor(self) -> Actor:
        return Actor(role=self.membership.role, team_id=self.team.id, user_id=self.user.id)

    @property
    def name(self) -> str:
        return self.user.display_name

    def resource(self, **kwargs) -> Resource:
        return Resource(team_id=self.team.id, **kwargs)


def get_context(
    db: DbSession = DbDep,  # type: ignore[assignment]
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> RequestContext:
    if not token:
        raise NotAuthenticatedError()

    from app.security import hash_token

    auth = db.execute(
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    ).scalar_one_or_none()
    if auth is None:
        raise NotAuthenticatedError("Your session has expired. Sign in again.")

    user = db.get(User, auth.user_id)
    if user is None or user.deleted_at is not None:
        raise NotAuthenticatedError("This account is no longer active.")

    membership = (
        db.execute(
            select(Membership)
            .where(
                Membership.user_id == user.id,
                Membership.status == MembershipStatus.ACTIVE.value,
            )
            .order_by(Membership.joined_at)
        )
        .scalars()
        .first()
    )
    if membership is None:
        raise AppError("You are not a member of any team yet.", code="team.missing")

    team = db.get(Team, membership.team_id)
    if team is None or team.deleted_at is not None:
        raise AppError("That team no longer exists.", code="team.missing")

    user.last_seen_at = datetime.now(timezone.utc)
    db.flush()
    return RequestContext(user=user, membership=membership, team=team, auth_session=auth)


ContextDep = Depends(get_context)


def require_capability(capability: str):
    """Dependency factory for team-level capabilities."""

    def dependency(context: RequestContext = ContextDep) -> RequestContext:  # type: ignore[assignment]
        if not can(context.actor, capability, Resource(team_id=context.team.id)):
            log_denial(context.actor, capability)
            raise PermissionDeniedError()
        return context

    return Depends(dependency)


def ensure_can(actor: Actor, capability: str, resource: Resource | None = None) -> None:
    """For entity-level decisions, where the caller has loaded the target already."""
    if not can(actor, capability, resource):
        log_denial(actor, capability)
        raise PermissionDeniedError()


def log_denial(actor: Actor, capability: str) -> None:
    """A refused action is part of the record.

    Written in its own short transaction so it survives even when the refused
    request rolls back. Admin-visible only: this is an audit fact, not a
    scoreboard, and it must never become a way to watch people.
    """
    if actor.team_id is None:
        return
    from app.services.activity import record_activity

    try:
        with get_session_factory()() as db:
            record_activity(
                db,
                team_id=actor.team_id,
                actor=actor,
                verb="permission.denied",
                target_type="permission",
                target_id=None,
                payload={"action": capability},
            )
            db.commit()
    except Exception:  # pragma: no cover - a refusal must not fail because of logging
        logging.getLogger("mshikaki").exception("could not record a refused action")


def is_owner(context: RequestContext) -> bool:
    return context.membership.role == TeamRole.OWNER.value


def get_settings_dep():
    return get_settings()
