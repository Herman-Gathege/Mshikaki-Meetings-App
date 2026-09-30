"""One flat comment thread per target."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can
from app.schemas import CommentCreateRequest
from app.services import work

router = APIRouter(tags=["comments"])


@router.get("/comments")
def list_comments(
    target_type: str,
    target_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    comments = work.list_comments(
        db, team_id=context.team.id, target_type=target_type, target_id=target_id
    )
    return {"items": [work.comment_row(comment) for comment in comments]}


@router.post("/comments")
def create_comment(
    payload: CommentCreateRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    ensure_can(context.actor, "comment.create")
    comment = work.create_comment(
        db,
        team_id=context.team.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        body=payload.body,
        actor=context.actor,
        actor_name=context.name,
    )
    return work.comment_row(comment)


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    comment = work.get_comment(db, team_id=context.team.id, comment_id=comment_id)
    if comment.author_id == context.user.id:
        ensure_can(context.actor, "comment.delete.own")
    else:
        ensure_can(context.actor, "comment.delete.any")
    work.delete_comment(db, comment=comment, actor=context.actor, actor_name=context.name)
    return {"status": "deleted"}
