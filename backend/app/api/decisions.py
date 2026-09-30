"""Decisions: recorded agreements that can be superseded."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can, require_capability
from app.domain.permissions import Resource
from app.schemas import DecisionCreateRequest, DecisionSupersedeRequest
from app.services import activity as activity_service
from app.services import work

router = APIRouter(tags=["decisions"])


def decision_resource(context, decision) -> Resource:
    return Resource(team_id=context.team.id, session_id=decision.session_id)


@router.get("/decisions")
def list_decisions(
    session_id: uuid.UUID | None = None,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    decisions = work.list_decisions(db, team_id=context.team.id, session_id=session_id)
    return {
        "items": [work.decision_row(db, decision) for decision in decisions],
        "total": len(decisions),
    }


@router.post("/decisions")
def record_decision(
    payload: DecisionCreateRequest,
    context=require_capability("decision.record"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    decision = work.record_decision(
        db,
        team_id=context.team.id,
        actor=context.actor,
        actor_name=context.name,
        statement=payload.statement,
        session_id=payload.session_id,
        idea_id=payload.idea_id,
        rationale=payload.rationale,
        standalone_reason=payload.standalone_reason,
    )
    return work.decision_row(db, decision)


@router.get("/decisions/{decision_id}")
def get_decision(
    decision_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    decision = work.get_decision(db, team_id=context.team.id, decision_id=decision_id)
    history = activity_service.for_target(
        db, team_id=context.team.id, target_type="decision", target_id=decision.id
    )
    comments = work.list_comments(
        db, team_id=context.team.id, target_type="decision", target_id=decision.id
    )
    return {
        **work.decision_row(db, decision),
        "comments": [work.comment_row(comment) for comment in comments],
        "activity": [activity_service.serialize(row) for row in history],
    }


@router.post("/decisions/{decision_id}/supersede")
def supersede_decision(
    decision_id: uuid.UUID,
    payload: DecisionSupersedeRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    decision = work.get_decision(db, team_id=context.team.id, decision_id=decision_id)
    ensure_can(context.actor, "decision.edit.any", decision_resource(context, decision))
    replacement = work.supersede_decision(
        db,
        decision=decision,
        statement=payload.statement,
        rationale=payload.rationale,
        actor=context.actor,
        actor_name=context.name,
    )
    return work.decision_row(db, replacement)
