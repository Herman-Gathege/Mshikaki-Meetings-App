"""Team, members, invites and guests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models import Guest, Invite, Membership, Team, User
from app.domain.enums import MembershipStatus, TeamRole
from app.errors import AppError, ConflictError, NotFoundError
from app.security import new_invite_code
from app.services.activity import record_activity


def list_members(db: DbSession, team_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.team_id == team_id, User.deleted_at.is_(None))
        .order_by(Membership.joined_at)
    ).all()
    return [
        {
            "membership_id": str(membership.id),
            "user_id": str(user.id),
            "name": user.display_name,
            "email": user.email,
            "role": membership.role,
            "status": membership.status,
            "joined_at": membership.joined_at.isoformat(),
            "leaderboard_opt_out": user.leaderboard_opt_out,
        }
        for membership, user in rows
    ]


def member_user(db: DbSession, team_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = (
        db.execute(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.team_id == team_id,
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        .scalars()
        .first()
    )
    if user is None:
        raise NotFoundError("That person is not in this team.")
    return user


def change_role(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    membership_id: uuid.UUID,
    role: str,
    actor,
    actor_name: str,
) -> Membership:
    if role not in {r.value for r in TeamRole if r != TeamRole.GUEST}:
        raise AppError("That is not a role we hand out.", code="role.invalid")

    membership = db.get(Membership, membership_id)
    if membership is None or membership.team_id != team_id:
        raise NotFoundError("That membership does not exist.")

    previous = membership.role
    if previous == TeamRole.OWNER.value and role != TeamRole.OWNER.value:
        _ensure_another_owner_exists(db, team_id, excluding=membership.id)

    membership.role = role
    db.flush()

    user = db.get(User, membership.user_id)
    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="member.role_changed",
        target_type="member",
        target_id=membership.user_id,
        payload={"name": user.display_name if user else "someone", "old": previous, "new": role},
    )
    return membership


def _ensure_another_owner_exists(
    db: DbSession, team_id: uuid.UUID, *, excluding: uuid.UUID
) -> None:
    other = db.execute(
        select(Membership.id).where(
            Membership.team_id == team_id,
            Membership.role == TeamRole.OWNER.value,
            Membership.id != excluding,
            Membership.status == MembershipStatus.ACTIVE.value,
        )
    ).first()
    if other is None:
        raise ConflictError("A team must keep at least one owner.")


def remove_member(
    db: DbSession, *, team_id: uuid.UUID, membership_id: uuid.UUID, actor, actor_name: str
) -> None:
    membership = db.get(Membership, membership_id)
    if membership is None or membership.team_id != team_id:
        raise NotFoundError("That membership does not exist.")
    if membership.role == TeamRole.OWNER.value:
        _ensure_another_owner_exists(db, team_id, excluding=membership.id)

    user = db.get(User, membership.user_id)
    membership.status = MembershipStatus.SUSPENDED.value
    db.delete(membership)
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="member.removed",
        target_type="member",
        target_id=membership.user_id,
        payload={"name": user.display_name if user else "someone"},
    )


def create_invite(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    role: str,
    email: str | None,
    actor,
    actor_name: str,
) -> Invite:
    invite = Invite(
        team_id=team_id,
        email=email.strip().lower() if email else None,
        code=new_invite_code(),
        role=role,
        invited_by=actor.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(invite)
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="invite.created",
        target_type="invite",
        target_id=invite.id,
        payload={"name": email or "someone", "role": role, "code": invite.code},
    )
    return invite


def list_invites(db: DbSession, team_id: uuid.UUID) -> list[Invite]:
    return list(
        db.execute(
            select(Invite)
            .where(Invite.team_id == team_id, Invite.accepted_at.is_(None))
            .order_by(Invite.created_at.desc())
        ).scalars()
    )


def find_invite(db: DbSession, code: str) -> Invite:
    invite = db.execute(
        select(Invite).where(Invite.code == code.strip().upper(), Invite.accepted_at.is_(None))
    ).scalar_one_or_none()
    if invite is None:
        raise NotFoundError("That invite code is not valid.")
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
        raise AppError("That invite has expired.", code="invite.expired")
    return invite


def create_guest(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    display_name: str,
    email: str | None,
    actor,
    actor_name: str,
) -> Guest:
    guest = Guest(
        team_id=team_id,
        display_name=display_name.strip(),
        email=email.strip().lower() if email else None,
        created_by=actor.user_id,
    )
    db.add(guest)
    db.flush()
    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="guest.created",
        target_type="guest",
        target_id=guest.id,
        payload={"name": guest.display_name},
    )
    return guest


def list_guests(db: DbSession, team_id: uuid.UUID) -> list[Guest]:
    return list(
        db.execute(
            select(Guest).where(Guest.team_id == team_id).order_by(Guest.display_name)
        ).scalars()
    )


def claim_guest(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    guest_id: uuid.UUID,
    user_id: uuid.UUID,
    actor,
    actor_name: str,
) -> Guest:
    """Link a guest to a real account without rewriting history.

    The strategy is deliberately additive: the guest row points at the user, and
    every historical activity row keeps its original actor. Nothing is rewritten.
    """
    guest = db.get(Guest, guest_id)
    if guest is None or guest.team_id != team_id:
        raise NotFoundError("That guest does not exist.")
    if guest.linked_user_id is not None and guest.linked_user_id != user_id:
        raise ConflictError("That guest is already linked to another profile.")

    guest.linked_user_id = user_id
    db.flush()
    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="guest.claimed",
        target_type="guest",
        target_id=guest.id,
        payload={"name": guest.display_name},
    )
    return guest


def email_domain_ok(email: str, allowed: tuple[str, ...]) -> bool:
    if not allowed:
        return True
    domain = email.strip().lower().rsplit("@", 1)[-1]
    return any(domain == item or domain.endswith(f".{item}") for item in allowed)


def update_team(
    db: DbSession,
    *,
    team: Team,
    name: str | None,
    description: str | None,
    timezone_name: str | None,
) -> Team:
    if name is not None:
        team.name = name.strip()
    if description is not None:
        team.description = description
    if timezone_name is not None:
        team.timezone = timezone_name
    db.flush()
    return team
