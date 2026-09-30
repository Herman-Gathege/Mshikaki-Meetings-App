"""Registration, login and sessions."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.db.models import AuthSession, Invite, Membership, Organization, Team, User
from app.domain.enums import MembershipStatus, TeamRole
from app.domain.permissions import Actor
from app.errors import AppError, ConflictError
from app.security import hash_password, hash_token, new_session_token, verify_password
from app.services.activity import record_activity


class InvalidCredentials(AppError):
    code = "auth.invalid_credentials"
    status_code = 401
    message = "That email and password combination is not right."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "mshikaki"


def unique_slug(db: DbSession, model, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    suffix = 2
    while db.execute(select(model.id).where(model.slug == candidate)).first() is not None:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def actor_for(user: User, team_id: uuid.UUID, role: str) -> Actor:
    return Actor(role=role, team_id=team_id, user_id=user.id)


def register(
    db: DbSession,
    *,
    email: str,
    display_name: str,
    password: str,
    team_name: str | None = None,
    invite: Invite | None = None,
) -> tuple[User, Membership, Team]:
    """Create a user, then either join their invited team or start a new one."""
    normalized = normalize_email(email)
    if db.execute(select(User.id).where(User.email == normalized)).first() is not None:
        raise ConflictError("That email is already registered.", field="email")

    user = User(
        email=normalized,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        timezone=get_settings().team_timezone,
    )
    db.add(user)
    db.flush()

    if invite is not None:
        team = db.get(Team, invite.team_id)
        if team is None or team.deleted_at is not None:
            raise AppError("That invite is no longer valid.", code="invite.invalid")
        membership = Membership(
            user_id=user.id,
            team_id=team.id,
            role=invite.role,
            status=MembershipStatus.ACTIVE.value,
        )
        db.add(membership)
        db.flush()
        invite.accepted_at = datetime.now(timezone.utc)
        invite.accepted_by = user.id
    else:
        team, membership = _create_team_and_owner(
            db, user=user, name=team_name or f"{display_name.split(' ')[0]}'s team"
        )

    record_activity(
        db,
        team_id=team.id,
        actor=actor_for(user, team.id, membership.role),
        actor_name=user.display_name,
        verb="member.joined",
        target_type="team",
        target_id=team.id,
        payload={"role": membership.role, "name": user.display_name},
    )
    return user, membership, team


def _create_team_and_owner(db: DbSession, *, user: User, name: str) -> tuple[Team, Membership]:
    organization = (
        db.execute(select(Organization).order_by(Organization.created_at)).scalars().first()
    )
    if organization is None:
        organization = Organization(name=name, slug=unique_slug(db, Organization, name))
        db.add(organization)
        db.flush()

    team = Team(
        organization_id=organization.id,
        name=name.strip(),
        slug=unique_slug(db, Team, name),
        timezone=get_settings().team_timezone,
    )
    db.add(team)
    db.flush()

    membership = Membership(
        user_id=user.id,
        team_id=team.id,
        role=TeamRole.OWNER.value,
        status=MembershipStatus.ACTIVE.value,
    )
    db.add(membership)
    db.flush()
    return team, membership


def authenticate(db: DbSession, *, email: str, password: str) -> User:
    user = db.execute(
        select(User).where(User.email == normalize_email(email), User.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is None or not verify_password(user.password_hash, password):
        raise InvalidCredentials()
    return user


def active_membership(db: DbSession, user_id: uuid.UUID) -> Membership | None:
    return (
        db.execute(
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE.value,
            )
            .order_by(Membership.joined_at)
        )
        .scalars()
        .first()
    )


def start_auth_session(
    db: DbSession, *, user: User, user_agent: str | None = None, ip: str | None = None
) -> str:
    """Returns the raw token; only its hash is stored."""
    settings = get_settings()
    token = new_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
            user_agent=(user_agent or "")[:300] or None,
            ip=ip,
        )
    )
    db.flush()
    return token


def end_auth_session(db: DbSession, token: str) -> None:
    row = db.execute(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.flush()
