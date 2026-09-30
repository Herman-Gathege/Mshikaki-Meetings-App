"""The team: settings, members, invites and guests."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, require_capability
from app.schemas import (
    ClaimGuestRequest,
    GuestRequest,
    InviteRequest,
    RoleChangeRequest,
    TeamUpdateRequest,
)
from app.services import identity

router = APIRouter(tags=["team"])


@router.get("/team")
def get_team(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    members = identity.list_members(db, context.team.id)
    return {
        "id": str(context.team.id),
        "name": context.team.name,
        "description": context.team.description,
        "timezone": context.team.timezone,
        "role": context.membership.role,
        "members": len(members),
    }


@router.patch("/team")
def update_team(
    payload: TeamUpdateRequest,
    context=require_capability("team.manage_settings"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    team = identity.update_team(
        db,
        team=context.team,
        name=payload.name,
        description=payload.description,
        timezone_name=payload.timezone,
    )
    return {"id": str(team.id), "name": team.name, "timezone": team.timezone}


@router.get("/team/members")
def list_members(context=ContextDep, db: DbSession = DbDep) -> dict:
    members = identity.list_members(db, context.team.id)
    return {"items": members, "total": len(members)}


@router.patch("/team/members/{membership_id}")
def change_role(
    membership_id: uuid.UUID,
    payload: RoleChangeRequest,
    context=require_capability("team.manage_members"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    membership = identity.change_role(
        db,
        team_id=context.team.id,
        membership_id=membership_id,
        role=payload.role,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"membership_id": str(membership.id), "role": membership.role}


@router.delete("/team/members/{membership_id}")
def remove_member(
    membership_id: uuid.UUID,
    context=require_capability("team.manage_members"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    identity.remove_member(
        db,
        team_id=context.team.id,
        membership_id=membership_id,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"status": "removed"}


@router.get("/team/invites")
def list_invites(context=require_capability("invite.create"), db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    invites = identity.list_invites(db, context.team.id)
    return {
        "items": [
            {
                "id": str(invite.id),
                "code": invite.code,
                "email": invite.email,
                "role": invite.role,
                "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
            }
            for invite in invites
        ]
    }


@router.post("/team/invites")
def create_invite(
    payload: InviteRequest,
    context=require_capability("invite.create"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    invite = identity.create_invite(
        db,
        team_id=context.team.id,
        role=payload.role,
        email=payload.email,
        actor=context.actor,
        actor_name=context.name,
    )
    return {
        "id": str(invite.id),
        "code": invite.code,
        "email": invite.email,
        "role": invite.role,
    }


@router.get("/team/guests")
def list_guests(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    guests = identity.list_guests(db, context.team.id)
    return {
        "items": [
            {
                "id": str(guest.id),
                "display_name": guest.display_name,
                "email": guest.email,
                "linked_user_id": str(guest.linked_user_id) if guest.linked_user_id else None,
            }
            for guest in guests
        ]
    }


@router.post("/guest-requests")
def create_guest(
    payload: GuestRequest,
    context=require_capability("session.participant.manage"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    guest = identity.create_guest(
        db,
        team_id=context.team.id,
        display_name=payload.display_name,
        email=payload.email,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"id": str(guest.id), "display_name": guest.display_name}


@router.post("/guests/{guest_id}/claim")
def claim_guest(
    guest_id: uuid.UUID,
    payload: ClaimGuestRequest,
    context=require_capability("team.manage_members"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    guest = identity.claim_guest(
        db,
        team_id=context.team.id,
        guest_id=guest_id,
        user_id=payload.user_id,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"id": str(guest.id), "linked_user_id": str(guest.linked_user_id)}
