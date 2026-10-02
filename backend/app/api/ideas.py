"""Ideas: capture, discuss, promote."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can, require_capability
from app.domain.permissions import Resource
from app.schemas import IdeaConvertRequest, IdeaCreateRequest, IdeaUpdateRequest
from app.services import activity as activity_service
from app.services import work

router = APIRouter(tags=["ideas"])


def idea_resource(context, idea) -> Resource:
    return Resource(
        team_id=context.team.id,
        owner_id=idea.created_by,
        session_id=idea.session_id,
    )


@router.get("/ideas")
def list_ideas(
    status: str | None = None,
    session_id: uuid.UUID | None = None,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    ideas = work.list_ideas(db, team_id=context.team.id, status=status, session_id=session_id)
    return {"items": [work.idea_row(db, idea) for idea in ideas], "total": len(ideas)}


@router.post("/ideas")
def create_idea(
    payload: IdeaCreateRequest,
    context=require_capability("idea.create"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    idea = work.create_idea(
        db,
        team_id=context.team.id,
        actor=context.actor,
        actor_name=context.name,
        title=payload.title,
        description=payload.description,
        session_id=payload.session_id,
        agenda_item_id=payload.agenda_item_id,
        tags=payload.tags,
    )
    return work.idea_row(db, idea)


@router.get("/ideas/{idea_id}")
def get_idea(
    idea_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    idea = work.get_idea(db, team_id=context.team.id, idea_id=idea_id)
    comments = work.list_comments(
        db, team_id=context.team.id, target_type="idea", target_id=idea.id
    )
    history = activity_service.for_target(
        db, team_id=context.team.id, target_type="idea", target_id=idea.id
    )
    visible = work.user_name(db, context.user.id) == context.name
    return {
        **work.idea_row(db, idea),
        "comments": [work.comment_row(comment) for comment in comments],
        "activity": [
            activity_service.serialize(row, viewer_can_see_admin=visible) for row in history
        ],
    }


@router.patch("/ideas/{idea_id}")
def update_idea(
    idea_id: uuid.UUID,
    payload: IdeaUpdateRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    idea = work.get_idea(db, team_id=context.team.id, idea_id=idea_id)
    can_edit_own = work.idea_row(db, idea)["author"]["id"] == str(context.user.id)
    if can_edit_own:
        ensure_can(context.actor, "idea.edit.own", idea_resource(context, idea))
    else:
        ensure_can(context.actor, "idea.edit.any", idea_resource(context, idea))
    work.update_idea(
        db,
        idea=idea,
        actor=context.actor,
        actor_name=context.name,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        tags=payload.tags,
    )
    return work.idea_row(db, idea)


@router.post("/ideas/{idea_id}/convert")
def convert_idea(
    idea_id: uuid.UUID,
    payload: IdeaConvertRequest,
    context=require_capability("idea.convert"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    idea = work.get_idea(db, team_id=context.team.id, idea_id=idea_id)
    work.convert_idea(
        db,
        idea=idea,
        target_type=payload.target_type,
        target_id=payload.target_id,
        actor=context.actor,
        actor_name=context.name,
    )
    return work.idea_row(db, idea)


@router.delete("/ideas/{idea_id}")
def delete_idea(
    idea_id: uuid.UUID,
    context=require_capability("idea.delete.any"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    idea = work.get_idea(db, team_id=context.team.id, idea_id=idea_id)
    work.delete_idea(db, idea=idea, actor=context.actor, actor_name=context.name)
    return {"status": "deleted"}
