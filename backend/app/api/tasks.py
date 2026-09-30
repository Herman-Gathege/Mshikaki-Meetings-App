"""Tasks and blockers: the actionable layer."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can, require_capability
from app.domain.permissions import Resource
from app.schemas import (
    BlockerCreateRequest,
    BlockerResolveRequest,
    CollaboratorRequest,
    TaskAssignRequest,
    TaskCreateRequest,
    TaskStatusRequest,
    TaskUpdateRequest,
)
from app.services import activity as activity_service
from app.services import work

router = APIRouter(tags=["tasks"])


def task_resource(context, task) -> Resource:
    return Resource(
        team_id=context.team.id,
        owner_id=task.owner_id,
        session_id=task.session_id,
        collaborator_ids=frozenset(c.user_id for c in task.collaborators),
    )


@router.get("/tasks")
def list_tasks(
    status: str | None = None,
    owner_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    include_closed: bool = True,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    tasks = work.list_tasks(
        db,
        team_id=context.team.id,
        status=status,
        owner_id=owner_id,
        project_id=project_id,
        session_id=session_id,
        include_closed=include_closed,
    )
    return {"items": [work.task_row(db, task) for task in tasks], "total": len(tasks)}


@router.get("/tasks/mine")
def my_tasks(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    tasks = work.my_tasks(db, team_id=context.team.id, user_id=context.user.id)
    return {"items": [work.task_row(db, task) for task in tasks], "total": len(tasks)}


@router.post("/tasks")
def create_task(
    payload: TaskCreateRequest,
    context=require_capability("task.create"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    if payload.owner_id is not None and payload.owner_id != context.user.id:
        ensure_can(
            context.actor,
            "task.assign.other",
            Resource(team_id=context.team.id, session_id=payload.session_id),
        )
    task = work.create_task(
        db,
        team_id=context.team.id,
        actor=context.actor,
        actor_name=context.name,
        title=payload.title,
        description=payload.description,
        owner_id=payload.owner_id,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        project_id=payload.project_id,
        session_id=payload.session_id,
        idea_id=payload.idea_id,
        decision_id=payload.decision_id,
        collaborator_ids=payload.collaborator_ids,
    )
    return work.task_row(db, task)


@router.get("/tasks/{task_id}")
def get_task(
    task_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    history = activity_service.for_target(
        db, team_id=context.team.id, target_type="task", target_id=task.id
    )
    comments = work.list_comments(
        db, team_id=context.team.id, target_type="task", target_id=task.id
    )
    return {
        **work.task_row(db, task),
        "comments": [work.comment_row(comment) for comment in comments],
        "activity": [activity_service.serialize(row) for row in history],
    }


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    resource = task_resource(context, task)
    if not (_try(context, "task.edit.own", resource) or _try(context, "task.edit.any", resource)):
        ensure_can(context.actor, "task.edit.any", resource)
    work.update_task(
        db,
        task=task,
        actor=context.actor,
        actor_name=context.name,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        due_date_provided="due_date" in payload.model_fields_set,
        project_id=payload.project_id,
        project_provided="project_id" in payload.model_fields_set,
    )
    return work.task_row(db, task)


def _try(context, capability: str, resource: Resource) -> bool:
    from app.domain.permissions import can

    return can(context.actor, capability, resource)


@router.post("/tasks/{task_id}/assign")
def assign_task(
    task_id: uuid.UUID,
    payload: TaskAssignRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    if payload.owner_id is not None and payload.owner_id != context.user.id:
        ensure_can(context.actor, "task.assign.other", task_resource(context, task))
    else:
        ensure_can(context.actor, "task.assign.self", task_resource(context, task))
    work.assign_task(
        db,
        task=task,
        owner_id=payload.owner_id,
        actor=context.actor,
        actor_name=context.name,
    )
    return work.task_row(db, task)


@router.post("/tasks/{task_id}/status")
def change_status(
    task_id: uuid.UUID,
    payload: TaskStatusRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    resource = task_resource(context, task)
    if not (
        _try(context, "task.status.own", resource) or _try(context, "task.status.any", resource)
    ):
        ensure_can(context.actor, "task.status.any", resource)
    work.change_task_status(
        db,
        task=task,
        status=payload.status,
        reason=payload.reason,
        actor=context.actor,
        actor_name=context.name,
    )
    return work.task_row(db, task)


@router.post("/tasks/{task_id}/collaborators")
def add_collaborator(
    task_id: uuid.UUID,
    payload: CollaboratorRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    ensure_can(context.actor, "task.edit.any", task_resource(context, task))
    work.add_collaborator(
        db, task=task, user_id=payload.user_id, actor=context.actor, actor_name=context.name
    )
    return work.task_row(db, task)


@router.delete("/tasks/{task_id}/collaborators/{user_id}")
def remove_collaborator(
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    ensure_can(context.actor, "task.edit.any", task_resource(context, task))
    work.remove_collaborator(
        db, task=task, user_id=user_id, actor=context.actor, actor_name=context.name
    )
    return work.task_row(db, task)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: uuid.UUID,
    context=require_capability("task.delete.any"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    work.delete_task(db, task=task, actor=context.actor, actor_name=context.name)
    return {"status": "deleted"}


@router.post("/tasks/{task_id}/blockers")
def raise_blocker(
    task_id: uuid.UUID,
    payload: BlockerCreateRequest,
    context=require_capability("blocker.raise"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    task = work.get_task(db, team_id=context.team.id, task_id=task_id)
    blocker = work.raise_blocker(
        db,
        task=task,
        reason=payload.reason,
        actor=context.actor,
        actor_name=context.name,
    )
    return {**work.task_row(db, task), "blocker": work.blocker_row(db, blocker)}


@router.post("/blockers/{blocker_id}/resolve")
def resolve_blocker(
    blocker_id: uuid.UUID,
    payload: BlockerResolveRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    blocker = work.get_blocker(db, team_id=context.team.id, blocker_id=blocker_id)
    task = (
        work.get_task(db, team_id=context.team.id, task_id=blocker.task_id)
        if blocker.task_id
        else None
    )
    if task is not None:
        ensure_can(context.actor, "blocker.resolve", task_resource(context, task))
    work.resolve_blocker(
        db,
        blocker=blocker,
        resolution=payload.resolution,
        actor=context.actor,
        actor_name=context.name,
    )
    return work.blocker_row(db, blocker)


@router.get("/blockers")
def list_blockers(
    open_only: bool = True,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    blockers = work.list_blockers(db, team_id=context.team.id, open_only=open_only)
    return {"items": [work.blocker_row(db, blocker) for blocker in blockers]}
