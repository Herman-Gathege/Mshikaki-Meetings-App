"""Projects: a flat container for work that outlives meetings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can, require_capability
from app.domain.permissions import Resource
from app.schemas import ProjectCreateRequest, ProjectUpdateRequest
from app.services import activity as activity_service
from app.services import work

router = APIRouter(tags=["projects"])


@router.get("/projects")
def list_projects(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    projects = work.list_projects(db, team_id=context.team.id)
    return {"items": [work.project_row(db, project) for project in projects]}


@router.post("/projects")
def create_project(
    payload: ProjectCreateRequest,
    context=require_capability("project.create"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    project = work.create_project(
        db,
        team_id=context.team.id,
        actor=context.actor,
        actor_name=context.name,
        name=payload.name,
        description=payload.description,
        owner_id=payload.owner_id,
    )
    return work.project_row(db, project)


@router.get("/projects/{project_id}")
def get_project(
    project_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    project = work.get_project(db, team_id=context.team.id, project_id=project_id)
    tasks = work.list_tasks(db, team_id=context.team.id, project_id=project.id)
    decisions = work.list_decisions(db, team_id=context.team.id)
    history = activity_service.for_target(
        db, team_id=context.team.id, target_type="project", target_id=project.id
    )
    linked_decisions = [
        work.decision_row(db, decision)
        for decision in decisions
        if any(task.decision_id == decision.id for task in tasks)
    ]
    return {
        **work.project_row(db, project),
        "tasks": [work.task_row(db, task) for task in tasks],
        "decisions": linked_decisions,
        "activity": [activity_service.serialize(row) for row in history],
    }


@router.patch("/projects/{project_id}")
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    project = work.get_project(db, team_id=context.team.id, project_id=project_id)
    ensure_can(
        context.actor,
        "project.manage",
        Resource(team_id=context.team.id, owner_id=project.owner_id),
    )
    work.update_project(
        db,
        project=project,
        actor=context.actor,
        actor_name=context.name,
        name=payload.name,
        description=payload.description,
        status=payload.status,
    )
    return work.project_row(db, project)
