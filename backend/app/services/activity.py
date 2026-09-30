"""The one place activity rows are written, and the ways they are read.

Every mutating service calls `record_activity` in the same transaction as the
change it describes, so the record and the work can never disagree. This module is
reviewed as security-relevant code: a gap here is a gap in the product's promise.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DbSession

from app.db.models import Activity
from app.domain import activity as activity_domain
from app.domain.enums import ActivityVisibility, ActorType
from app.domain.permissions import Actor


def record_activity(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    verb: str,
    target_type: str,
    target_id: uuid.UUID | None,
    actor: Actor | None = None,
    actor_name: str | None = None,
    payload: dict[str, Any] | None = None,
    session_id: uuid.UUID | None = None,
    source: str = "web",
) -> Activity:
    """Write one audit record. Raises on an unknown verb rather than guessing."""
    spec = activity_domain.spec(verb)  # UnknownVerb for anything not whitelisted

    if actor is None or (actor.user_id is None and actor.guest_id is None):
        actor_type = ActorType.SYSTEM.value
        actor_id = None
        resolved_name = actor_name or "Mshikaki"
    elif actor.guest_id is not None and actor.user_id is None:
        actor_type = ActorType.GUEST.value
        actor_id = actor.guest_id
        resolved_name = actor_name or "A guest"
    else:
        actor_type = ActorType.USER.value
        actor_id = actor.user_id
        resolved_name = actor_name or "Someone"

    row = Activity(
        team_id=team_id,
        session_id=session_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=resolved_name,
        verb=verb,
        target_type=target_type,
        target_id=target_id,
        payload=payload or {},
        occurred_at=datetime.now(timezone.utc),
        source=source,
        visibility=spec.visibility or ActivityVisibility.TEAM.value,
    )
    db.add(row)
    db.flush()
    return row


def serialize(row: Activity, *, viewer_can_see_admin: bool = False) -> dict[str, Any]:
    if row.visibility == ActivityVisibility.ADMIN.value and not viewer_can_see_admin:
        return {
            "id": str(row.id),
            "verb": "restricted",
            "description": "a team setting changed",
            "sentence": "Mshikaki recorded a team setting change",
            "actor_type": "system",
            "actor_name": "Mshikaki",
            "occurred_at": row.occurred_at.isoformat(),
            "target_type": row.target_type,
            "target_id": str(row.target_id) if row.target_id else None,
            "session_id": str(row.session_id) if row.session_id else None,
            "payload": {},
            "visibility": row.visibility,
            "source": row.source,
        }
    return {
        "id": str(row.id),
        "verb": row.verb,
        "description": activity_domain.describe(row.verb, row.payload),
        "sentence": activity_domain.full_sentence(row.actor_name, row.verb, row.payload),
        "actor_type": row.actor_type,
        "actor_name": row.actor_name,
        "occurred_at": row.occurred_at.isoformat(),
        "target_type": row.target_type,
        "target_id": str(row.target_id) if row.target_id else None,
        "session_id": str(row.session_id) if row.session_id else None,
        "payload": row.payload,
        "visibility": row.visibility,
        "source": row.source,
    }


def _base_query(team_id: uuid.UUID) -> Select[tuple[Activity]]:
    return (
        select(Activity)
        .where(Activity.team_id == team_id)
        .order_by(Activity.occurred_at.desc(), Activity.id.desc())
    )


def for_team(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    limit: int = 50,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    session_id: uuid.UUID | None = None,
) -> list[Activity]:
    query = _base_query(team_id)
    if actor_id is not None:
        query = query.where(Activity.actor_id == actor_id)
    if target_type is not None:
        query = query.where(Activity.target_type == target_type)
    if session_id is not None:
        query = query.where(Activity.session_id == session_id)
    return list(db.execute(query.limit(min(limit, 200))).scalars())


def for_target(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    limit: int = 100,
) -> list[Activity]:
    query = (
        select(Activity)
        .where(
            Activity.team_id == team_id,
            Activity.target_type == target_type,
            Activity.target_id == target_id,
        )
        .order_by(Activity.occurred_at.asc(), Activity.id.asc())
        .limit(min(limit, 200))
    )
    return list(db.execute(query).scalars())


def for_session(db: DbSession, *, session_id: uuid.UUID, limit: int = 200) -> list[Activity]:
    """Chronological and complete: what happened in this meeting, in order."""
    query = (
        select(Activity)
        .where(Activity.session_id == session_id)
        .order_by(Activity.occurred_at.asc(), Activity.id.asc())
        .limit(min(limit, 500))
    )
    return list(db.execute(query).scalars())


def count_for_session(db: DbSession, session_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count()).select_from(Activity).where(Activity.session_id == session_id)
        ).scalar_one()
    )
