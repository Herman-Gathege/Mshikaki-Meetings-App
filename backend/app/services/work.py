"""Ideas, decisions, projects, tasks, blockers and comments.

This is the layer where the product's promises are kept or broken:

* every mutation writes activity,
* task status and blocker records never disagree,
* origin links survive every later edit,
* and deletion is soft, so "why does this exist?" always has an answer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.db.models import (
    Blocker,
    Comment,
    Decision,
    Guest,
    Idea,
    IdeaTag,
    Project,
    Task,
    TaskCollaborator,
    User,
)
from app.domain import ideas as idea_rules
from app.domain import tasks as task_rules
from app.domain.enums import (
    COMMENT_TARGETS,
    CommentTarget,
    IdeaStatus,
    TaskPriority,
    TaskStatus,
)
from app.errors import AppError, NotFoundError, PermissionDeniedError
from app.services.activity import record_activity

CLOSED_TASK_STATUSES = {TaskStatus.DONE.value, TaskStatus.CANCELLED.value}


# --- serializers ---------------------------------------------------------------


def user_name(db: DbSession, user_id: uuid.UUID | None, fallback: str = "Someone") -> str:
    if user_id is None:
        return fallback
    user = db.get(User, user_id)
    return user.display_name if user else fallback


def task_row(db: DbSession, task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "owner": (
            {"id": str(task.owner_id), "name": user_name(db, task.owner_id)}
            if task.owner_id
            else None
        ),
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "project_id": str(task.project_id) if task.project_id else None,
        "origin": {
            "session_id": str(task.session_id) if task.session_id else None,
        "agenda_item_id": str(task.agenda_item_id) if task.agenda_item_id else None,
            "idea_id": str(task.idea_id) if task.idea_id else None,
            "decision_id": str(task.decision_id) if task.decision_id else None,
        },
        "collaborators": [
            {"id": str(c.user_id), "name": user_name(db, c.user_id)} for c in task.collaborators
        ],
        "open_blockers": [
            {
                "id": str(b.id),
                "reason": b.reason,
                "raised_by": b.raised_by_name,
                "raised_at": b.raised_at.isoformat() if b.raised_at else None,
            }
            for b in task.blockers
            if b.is_open
        ],
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def idea_row(db: DbSession, idea: Idea) -> dict:
    return {
        "id": str(idea.id),
        "title": idea.title,
        "description": idea.description,
        "status": idea.status,
        "author": {
            "id": str(idea.created_by) if idea.created_by else None,
            "name": idea.author_name,
        },
        "session_id": str(idea.session_id) if idea.session_id else None,
        "agenda_item_id": str(idea.agenda_item_id) if idea.agenda_item_id else None,
        "tags": [tag.tag for tag in idea.tags],
        "converted_to": (
            {"type": idea.converted_to_type, "id": str(idea.converted_to_id)}
            if idea.converted_to_type and idea.converted_to_id
            else None
        ),
        "created_at": idea.created_at.isoformat(),
    }


def decision_row(db: DbSession, decision: Decision) -> dict:
    return {
        "id": str(decision.id),
        "statement": decision.statement,
        "rationale": decision.rationale,
        "recorded_by": decision.decided_by_name,
        "session_id": str(decision.session_id) if decision.session_id else None,
        "agenda_item_id": str(decision.agenda_item_id) if decision.agenda_item_id else None,
        "idea_id": str(decision.idea_id) if decision.idea_id else None,
        "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
        "superseded_by_id": str(decision.superseded_by_id) if decision.superseded_by_id else None,
        "is_superseded": decision.superseded_by_id is not None,
    }


def blocker_row(db: DbSession, blocker: Blocker) -> dict:
    return {
        "id": str(blocker.id),
        "task_id": str(blocker.task_id) if blocker.task_id else None,
        "task_title": (db.get(Task, blocker.task_id).title if blocker.task_id else None),
        "reason": blocker.reason,
        "raised_by": blocker.raised_by_name,
        "raised_at": blocker.raised_at.isoformat() if blocker.raised_at else None,
        "resolved_by": blocker.resolved_by_name,
        "resolved_at": blocker.resolved_at.isoformat() if blocker.resolved_at else None,
        "resolution": blocker.resolution,
        "is_open": blocker.is_open,
    }


def project_row(db: DbSession, project: Project) -> dict:
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "owner": (
            {"id": str(project.owner_id), "name": user_name(db, project.owner_id)}
            if project.owner_id
            else None
        ),
    }


# --- ideas ---------------------------------------------------------------------


def create_idea(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    actor,
    actor_name: str,
    title: str,
    description: str | None = None,
    session_id: uuid.UUID | None = None,
    agenda_item_id: uuid.UUID | None = None,
    tags: list[str] | None = None,
) -> Idea:
    idea = Idea(
        team_id=team_id,
        session_id=session_id,
        agenda_item_id=agenda_item_id,
        title=title.strip()[:200],
        description=description,
        created_by=actor.user_id,
        author_name=actor_name,
        status=IdeaStatus.NEW.value,
    )
    db.add(idea)
    db.flush()
    for tag in {t.strip()[:60] for t in (tags or []) if t.strip()}:
        db.add(IdeaTag(idea_id=idea.id, tag=tag))
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        session_id=session_id,
        actor=actor,
        actor_name=actor_name,
        verb="idea.created",
        target_type="idea",
        target_id=idea.id,
        payload={"title": idea.title},
    )
    return idea


def update_idea(
    db: DbSession,
    *,
    idea: Idea,
    actor,
    actor_name: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
) -> Idea:
    changes: dict[str, object] = {}
    if title is not None and title.strip() and title.strip() != idea.title:
        changes["title"] = {"old": idea.title, "new": title.strip()[:200]}
        idea.title = title.strip()[:200]
    if description is not None and description != idea.description:
        changes["description"] = {"old": idea.description, "new": description}
        idea.description = description

    previous_status = idea.status
    if status is not None and status != idea.status:
        idea_rules.ensure_transition(idea.status, status)
        idea.status = status

    if tags is not None:
        for existing in list(idea.tags):
            db.delete(existing)
        db.flush()
        for tag in {t.strip()[:60] for t in tags if t.strip()}:
            db.add(IdeaTag(idea_id=idea.id, tag=tag))
        changes["tags"] = {"new": sorted({t.strip() for t in tags if t.strip()})}

    db.flush()

    if idea.status != previous_status:
        record_activity(
            db,
            team_id=idea.team_id,
            session_id=idea.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="idea.status_changed",
            target_type="idea",
            target_id=idea.id,
            payload={"title": idea.title, "old": previous_status, "new": idea.status},
        )
        _award_idea_accepted(
            db, idea=idea, actor=actor, actor_name=actor_name, previous=previous_status
        )
    elif changes:
        record_activity(
            db,
            team_id=idea.team_id,
            session_id=idea.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="idea.updated",
            target_type="idea",
            target_id=idea.id,
            payload={"title": idea.title, **changes},
        )
    return idea


def _award_idea_accepted(
    db: DbSession, *, idea: Idea, actor, actor_name: str, previous: str
) -> None:
    if idea.status != IdeaStatus.ACCEPTED.value or idea.created_by is None:
        return
    from app.services.bragging import award_for_event

    award_for_event(
        db,
        team_id=idea.team_id,
        user_id=idea.created_by,
        subject_name=idea.author_name,
        rule_key="idea_accepted",
        source_type="idea",
        source_id=idea.id,
        actor=actor,
        actor_name=actor_name,
    )


def delete_idea(db: DbSession, *, idea: Idea, actor, actor_name: str) -> None:
    snapshot = {"title": idea.title, "status": idea.status, "description": idea.description}
    idea.deleted_at = datetime.now(timezone.utc)
    db.flush()
    record_activity(
        db,
        team_id=idea.team_id,
        session_id=idea.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="idea.deleted",
        target_type="idea",
        target_id=idea.id,
        payload=snapshot,
    )


def convert_idea(
    db: DbSession,
    *,
    idea: Idea,
    target_type: str,
    target_id: uuid.UUID,
    actor,
    actor_name: str,
) -> Idea:
    if not idea_rules.can_convert(idea.status):
        raise AppError(
            f"An idea in '{idea.status}' cannot be converted.", code="idea.not_convertible"
        )
    idea.converted_to_type = target_type
    idea.converted_to_id = target_id
    idea.status = IdeaStatus.CONVERTED.value
    db.flush()
    record_activity(
        db,
        team_id=idea.team_id,
        session_id=idea.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="idea.converted",
        target_type="idea",
        target_id=idea.id,
        payload={"title": idea.title, "target_type": target_type, "target_id": str(target_id)},
    )
    return idea


def list_ideas(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    status: str | None = None,
    session_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Idea]:
    query = select(Idea).where(Idea.team_id == team_id, Idea.deleted_at.is_(None))
    if status:
        query = query.where(Idea.status == status)
    if session_id:
        query = query.where(Idea.session_id == session_id)
    return list(db.execute(query.order_by(Idea.created_at.desc()).limit(min(limit, 200))).scalars())


def get_idea(db: DbSession, *, team_id: uuid.UUID, idea_id: uuid.UUID) -> Idea:
    idea = db.execute(
        select(Idea).where(Idea.id == idea_id, Idea.team_id == team_id, Idea.deleted_at.is_(None))
    ).scalar_one_or_none()
    if idea is None:
        raise NotFoundError("That idea does not exist.")
    return idea


# --- decisions -----------------------------------------------------------------


def record_decision(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    actor,
    actor_name: str,
    statement: str,
    session_id: uuid.UUID | None = None,
    idea_id: uuid.UUID | None = None,
    agenda_item_id: uuid.UUID | None = None,
    rationale: str | None = None,
    standalone_reason: str | None = None,
) -> Decision:
    if session_id is None and not standalone_reason:
        raise AppError(
            "A decision outside a session needs a reason for the record.",
            code="decision.needs_context",
        )
    decision = Decision(
        team_id=team_id,
        session_id=session_id,
        idea_id=idea_id,
        agenda_item_id=agenda_item_id,
        statement=statement.strip(),
        rationale=rationale,
        decided_by=actor.user_id,
        decided_by_name=actor_name,
        decided_at=datetime.now(timezone.utc),
        standalone_reason=standalone_reason,
    )
    db.add(decision)
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        session_id=session_id,
        actor=actor,
        actor_name=actor_name,
        verb="decision.recorded",
        target_type="decision",
        target_id=decision.id,
        payload={"statement": decision.statement, "idea_id": str(idea_id) if idea_id else None},
    )

    if idea_id is not None:
        idea = db.get(Idea, idea_id)
        if idea is not None and idea.status != IdeaStatus.CONVERTED.value:
            convert_idea(
                db,
                idea=idea,
                target_type="decision",
                target_id=decision.id,
                actor=actor,
                actor_name=actor_name,
            )
    return decision


def supersede_decision(
    db: DbSession,
    *,
    decision: Decision,
    statement: str,
    rationale: str | None,
    actor,
    actor_name: str,
) -> Decision:
    replacement = Decision(
        team_id=decision.team_id,
        session_id=decision.session_id,
        idea_id=decision.idea_id,
        statement=statement.strip(),
        rationale=rationale,
        decided_by=actor.user_id,
        decided_by_name=actor_name,
        decided_at=datetime.now(timezone.utc),
        supersedes_id=decision.id,
    )
    db.add(replacement)
    db.flush()
    decision.superseded_by_id = replacement.id
    db.flush()

    record_activity(
        db,
        team_id=decision.team_id,
        session_id=decision.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="decision.superseded",
        target_type="decision",
        target_id=replacement.id,
        payload={"statement": decision.statement, "replacement": statement.strip()},
    )
    return replacement


def list_decisions(
    db: DbSession, *, team_id: uuid.UUID, session_id: uuid.UUID | None = None, limit: int = 100
) -> list[Decision]:
    query = select(Decision).where(Decision.team_id == team_id, Decision.deleted_at.is_(None))
    if session_id:
        query = query.where(Decision.session_id == session_id)
    return list(
        db.execute(
            query.order_by(Decision.decided_at.desc().nullslast()).limit(min(limit, 200))
        ).scalars()
    )


def get_decision(db: DbSession, *, team_id: uuid.UUID, decision_id: uuid.UUID) -> Decision:
    decision = db.execute(
        select(Decision).where(
            Decision.id == decision_id,
            Decision.team_id == team_id,
            Decision.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if decision is None:
        raise NotFoundError("That decision does not exist.")
    return decision


# --- projects ------------------------------------------------------------------


def create_project(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    actor,
    actor_name: str,
    name: str,
    description: str | None = None,
    owner_id: uuid.UUID | None = None,
) -> Project:
    project = Project(
        team_id=team_id,
        name=name.strip()[:200],
        description=description,
        owner_id=owner_id or actor.user_id,
    )
    db.add(project)
    db.flush()
    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="project.created",
        target_type="project",
        target_id=project.id,
        payload={"title": project.name},
    )
    return project


def get_project(db: DbSession, *, team_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = db.execute(
        select(Project).where(
            Project.id == project_id, Project.team_id == team_id, Project.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError("That project does not exist.")
    return project


def list_projects(db: DbSession, *, team_id: uuid.UUID) -> list[Project]:
    return list(
        db.execute(
            select(Project)
            .where(Project.team_id == team_id, Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
        ).scalars()
    )


def update_project(
    db: DbSession,
    *,
    project: Project,
    actor,
    actor_name: str,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
) -> Project:
    previous = project.status
    if name is not None and name.strip():
        project.name = name.strip()[:200]
    if description is not None:
        project.description = description
    if status is not None and status != project.status:
        project.status = status
    db.flush()

    verb = "project.status_changed" if status and status != previous else "project.updated"
    payload: dict[str, object] = {"title": project.name}
    if verb == "project.status_changed":
        payload.update({"old": previous, "new": project.status})
    record_activity(
        db,
        team_id=project.team_id,
        actor=actor,
        actor_name=actor_name,
        verb=verb,
        target_type="project",
        target_id=project.id,
        payload=payload,
    )
    return project


# --- tasks ---------------------------------------------------------------------


def create_task(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    actor,
    actor_name: str,
    title: str,
    description: str | None = None,
    owner_id: uuid.UUID | None = None,
    status: str = TaskStatus.BACKLOG.value,
    priority: str = TaskPriority.NORMAL.value,
    due_date: date | None = None,
    project_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    idea_id: uuid.UUID | None = None,
    decision_id: uuid.UUID | None = None,
    agenda_item_id: uuid.UUID | None = None,
    collaborator_ids: list[uuid.UUID] | None = None,
) -> Task:
    task_rules.ensure_owner(status, owner_id)

    task = Task(
        team_id=team_id,
        title=title.strip()[:200],
        description=description,
        owner_id=owner_id,
        status=status,
        priority=priority,
        due_date=due_date,
        project_id=project_id,
        session_id=session_id,
        idea_id=idea_id,
        decision_id=decision_id,
        agenda_item_id=agenda_item_id,
        created_by=actor.user_id,
    )
    db.add(task)
    db.flush()

    for collaborator_id in set(collaborator_ids or []):
        if collaborator_id and collaborator_id != owner_id:
            db.add(TaskCollaborator(task_id=task.id, user_id=collaborator_id))
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        session_id=session_id,
        actor=actor,
        actor_name=actor_name,
        verb="task.created",
        target_type="task",
        target_id=task.id,
        payload={
            "title": task.title,
            "owner_name": user_name(db, owner_id) if owner_id else None,
            "idea_id": str(idea_id) if idea_id else None,
            "decision_id": str(decision_id) if decision_id else None,
            "agenda_item_id": str(agenda_item_id) if agenda_item_id else None,
        },
    )
    return task


def get_task(db: DbSession, *, team_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = db.execute(
        select(Task).where(Task.id == task_id, Task.team_id == team_id, Task.deleted_at.is_(None))
    ).scalar_one_or_none()
    if task is None:
        raise NotFoundError("That task does not exist.")
    return task


def update_task(
    db: DbSession,
    *,
    task: Task,
    actor,
    actor_name: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    due_date: date | None = None,
    due_date_provided: bool = False,
    project_id: uuid.UUID | None = None,
    project_provided: bool = False,
) -> Task:
    if title is not None and title.strip() and title.strip() != task.title:
        previous = task.title
        task.title = title.strip()[:200]
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.updated",
            target_type="task",
            target_id=task.id,
            payload={"title": task.title, "old": {"title": previous}},
        )
    if description is not None:
        task.description = description
    if priority is not None and priority != task.priority:
        previous = task.priority
        task.priority = priority
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.priority_changed",
            target_type="task",
            target_id=task.id,
            payload={"title": task.title, "old": previous, "new": priority},
        )
    if due_date_provided and due_date != task.due_date:
        task.due_date = due_date
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.due_date_changed",
            target_type="task",
            target_id=task.id,
            payload={
                "title": task.title,
                "old": task.due_date.isoformat() if task.due_date else None,
                "new": due_date.isoformat() if due_date else None,
            },
        )
    if project_provided:
        task.project_id = project_id
    db.flush()
    return task


def assign_task(
    db: DbSession,
    *,
    task: Task,
    owner_id: uuid.UUID | None,
    actor,
    actor_name: str,
) -> Task:
    previous_id = task.owner_id
    previous_name = user_name(db, previous_id) if previous_id else None
    if owner_id is not None:
        _ensure_team_member(db, team_id=task.team_id, user_id=owner_id)
    task_rules.ensure_owner(task.status, owner_id)
    task.owner_id = owner_id
    db.flush()

    record_activity(
        db,
        team_id=task.team_id,
        session_id=task.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="task.assigned",
        target_type="task",
        target_id=task.id,
        payload={
            "title": task.title,
            "old": previous_name,
            "new": user_name(db, owner_id) if owner_id else "nobody",
        },
    )
    return task


def _ensure_team_member(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
    from app.db.models import Membership

    membership = db.execute(
        select(Membership).where(Membership.user_id == user_id, Membership.team_id == team_id)
    ).scalar_one_or_none()
    if membership is None:
        raise AppError("That person is not in this team.", code="task.owner_not_member")


def change_task_status(
    db: DbSession,
    *,
    task: Task,
    status: str,
    actor,
    actor_name: str,
    reason: str | None = None,
) -> Task:
    task_rules.ensure_transition(task.status, status)
    task_rules.ensure_owner(status, task.owner_id)

    previous = task.status
    open_blockers = [b for b in task.blockers if b.is_open]
    task_rules.ensure_blocker_state(status, has_open_blocker=bool(open_blockers))

    task.status = status
    if status == TaskStatus.DONE.value:
        task.completed_at = datetime.now(timezone.utc)
    elif previous == TaskStatus.DONE.value:
        task.completed_at = None
    db.flush()

    if previous == TaskStatus.DONE.value and status == TaskStatus.IN_PROGRESS.value:
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.reopened",
            target_type="task",
            target_id=task.id,
            payload={"title": task.title, "reason": reason or "no reason given"},
        )
    else:
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.status_changed",
            target_type="task",
            target_id=task.id,
            payload={"title": task.title, "old": previous, "new": status},
        )

    if status == TaskStatus.DONE.value and task.owner_id is not None:
        _award_task_completed(db, task=task, actor=actor, actor_name=actor_name)
    return task


def _award_task_completed(db: DbSession, *, task: Task, actor, actor_name: str) -> None:
    from app.services.bragging import award_for_event

    award_for_event(
        db,
        team_id=task.team_id,
        user_id=task.owner_id,
        subject_name=user_name(db, task.owner_id),
        rule_key="task_completed",
        source_type="task",
        source_id=task.id,
        session_id=task.session_id,
        actor=actor,
        actor_name=actor_name,
    )


def add_collaborator(
    db: DbSession, *, task: Task, user_id: uuid.UUID, actor, actor_name: str
) -> Task:
    _ensure_team_member(db, team_id=task.team_id, user_id=user_id)
    exists = db.execute(
        select(TaskCollaborator).where(
            TaskCollaborator.task_id == task.id, TaskCollaborator.user_id == user_id
        )
    ).scalar_one_or_none()
    if exists is None:
        db.add(TaskCollaborator(task_id=task.id, user_id=user_id))
        db.flush()
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.collaborator_added",
            target_type="task",
            target_id=task.id,
            payload={"title": task.title, "name": user_name(db, user_id)},
        )
    return task


def remove_collaborator(
    db: DbSession, *, task: Task, user_id: uuid.UUID, actor, actor_name: str
) -> Task:
    row = db.execute(
        select(TaskCollaborator).where(
            TaskCollaborator.task_id == task.id, TaskCollaborator.user_id == user_id
        )
    ).scalar_one_or_none()
    if row is not None:
        db.delete(row)
        db.flush()
        record_activity(
            db,
            team_id=task.team_id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
            verb="task.collaborator_removed",
            target_type="task",
            target_id=task.id,
            payload={"title": task.title, "name": user_name(db, user_id)},
        )
    return task


def delete_task(db: DbSession, *, task: Task, actor, actor_name: str) -> None:
    snapshot = {"title": task.title, "status": task.status, "owner": user_name(db, task.owner_id)}
    task.deleted_at = datetime.now(timezone.utc)
    db.flush()
    record_activity(
        db,
        team_id=task.team_id,
        session_id=task.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="task.deleted",
        target_type="task",
        target_id=task.id,
        payload=snapshot,
    )


def list_tasks(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    status: str | None = None,
    owner_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    idea_id: uuid.UUID | None = None,
    decision_id: uuid.UUID | None = None,
    include_closed: bool = True,
    limit: int = 200,
) -> list[Task]:
    query = select(Task).where(Task.team_id == team_id, Task.deleted_at.is_(None))
    if status:
        query = query.where(Task.status == status)
    elif not include_closed:
        query = query.where(Task.status.notin_(list(CLOSED_TASK_STATUSES)))
    if owner_id:
        query = query.where(Task.owner_id == owner_id)
    if project_id:
        query = query.where(Task.project_id == project_id)
    if session_id:
        query = query.where(Task.session_id == session_id)
    # The forward half of traceability: what did this idea or decision become?
    if idea_id:
        query = query.where(Task.idea_id == idea_id)
    if decision_id:
        query = query.where(Task.decision_id == decision_id)
    return list(
        db.execute(
            query.order_by(
                Task.status, Task.due_date.asc().nullslast(), Task.created_at.desc()
            ).limit(min(limit, 400))
        ).scalars()
    )


def my_tasks(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> list[Task]:
    """Everything I own or collaborate on, open first."""
    collaborative = select(TaskCollaborator.task_id).where(TaskCollaborator.user_id == user_id)
    query = (
        select(Task)
        .where(
            Task.team_id == team_id,
            Task.deleted_at.is_(None),
            or_(Task.owner_id == user_id, Task.id.in_(collaborative)),
        )
        .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
    )
    return list(db.execute(query).scalars())


# --- blockers ------------------------------------------------------------------


def raise_blocker(
    db: DbSession,
    *,
    task: Task,
    reason: str,
    actor,
    actor_name: str,
) -> Blocker:
    if task.status == TaskStatus.DONE.value:
        raise AppError("A finished task cannot be blocked.", code="blocker.task_done")
    if task.owner_id is None:
        raise AppError("Give the task an owner before blocking it.", code="blocker.owner_required")
    blocker = Blocker(
        team_id=task.team_id,
        task_id=task.id,
        reason=reason.strip(),
        raised_by=actor.user_id,
        raised_by_name=actor_name,
        raised_at=datetime.now(timezone.utc),
    )
    db.add(blocker)
    db.flush()

    if task.status == TaskStatus.IN_PROGRESS.value or task.status == TaskStatus.BACKLOG.value:
        task.status = TaskStatus.BLOCKED.value
    db.flush()

    record_activity(
        db,
        team_id=task.team_id,
        session_id=task.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="blocker.raised",
        target_type="task",
        target_id=task.id,
        payload={"title": task.title, "reason": blocker.reason},
    )
    return blocker


def resolve_blocker(
    db: DbSession,
    *,
    blocker: Blocker,
    resolution: str,
    actor,
    actor_name: str,
) -> Blocker:
    if not blocker.is_open:
        raise AppError("That blocker is already resolved.", code="blocker.already_resolved")
    blocker.resolution = resolution.strip()
    blocker.resolved_by = actor.user_id
    blocker.resolved_by_name = actor_name
    blocker.resolved_at = datetime.now(timezone.utc)
    db.flush()

    task = db.get(Task, blocker.task_id) if blocker.task_id else None
    if (
        task is not None
        and not any(b.is_open for b in task.blockers)
        and task.status == TaskStatus.BLOCKED.value
    ):
        task.status = TaskStatus.IN_PROGRESS.value
        db.flush()

    record_activity(
        db,
        team_id=blocker.team_id,
        session_id=task.session_id if task else None,
        actor=actor,
        actor_name=actor_name,
        verb="blocker.resolved",
        target_type="task",
        target_id=task.id if task else blocker.id,
        payload={
            "title": task.title if task else "a task",
            "resolution": blocker.resolution,
        },
    )

    if task is not None and task.status != TaskStatus.BLOCKED.value:
        from app.services.bragging import award_for_event

        award_for_event(
            db,
            team_id=blocker.team_id,
            user_id=actor.user_id,
            subject_name=actor_name,
            rule_key="blocker_resolved",
            source_type="blocker",
            source_id=blocker.id,
            session_id=task.session_id,
            actor=actor,
            actor_name=actor_name,
        )
    return blocker


def get_blocker(db: DbSession, *, team_id: uuid.UUID, blocker_id: uuid.UUID) -> Blocker:
    blocker = db.execute(
        select(Blocker).where(Blocker.id == blocker_id, Blocker.team_id == team_id)
    ).scalar_one_or_none()
    if blocker is None:
        raise NotFoundError("That blocker does not exist.")
    return blocker


def list_blockers(db: DbSession, *, team_id: uuid.UUID, open_only: bool = True) -> list[Blocker]:
    query = select(Blocker).where(Blocker.team_id == team_id)
    if open_only:
        query = query.where(Blocker.resolved_at.is_(None))
    return list(db.execute(query.order_by(Blocker.raised_at.asc())).scalars())


# --- comments ------------------------------------------------------------------


def create_comment(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    body: str,
    actor,
    actor_name: str,
) -> Comment:
    if target_type not in COMMENT_TARGETS:
        raise AppError("You cannot comment on that.", code="comment.bad_target")
    if not body.strip():
        raise AppError("Write something first.", code="comment.empty")

    comment = Comment(
        team_id=team_id,
        target_type=target_type,
        target_id=target_id,
        author_id=actor.user_id,
        author_name=actor_name,
        body=body.strip(),
    )
    db.add(comment)
    db.flush()
    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="comment.created",
        target_type=target_type,
        target_id=target_id,
        payload={
            "target_label": _target_label(db, team_id, target_type, target_id),
            "excerpt": body.strip()[:120],
        },
    )
    return comment


def _target_label(db: DbSession, team_id: uuid.UUID, target_type: str, target_id: uuid.UUID) -> str:
    model = {
        CommentTarget.IDEA.value: Idea,
        CommentTarget.DECISION.value: Decision,
        CommentTarget.TASK.value: Task,
    }.get(target_type)
    if model is None:
        return f"a {target_type}"
    row = db.get(model, target_id)
    if row is None:
        return f"a {target_type}"
    title = getattr(row, "title", None) or getattr(row, "statement", "an item")
    return f'the {target_type} "{title}"'


def list_comments(
    db: DbSession, *, team_id: uuid.UUID, target_type: str, target_id: uuid.UUID
) -> list[Comment]:
    return list(
        db.execute(
            select(Comment)
            .where(
                Comment.team_id == team_id,
                Comment.target_type == target_type,
                Comment.target_id == target_id,
                Comment.deleted_at.is_(None),
            )
            .order_by(Comment.created_at.asc())
        ).scalars()
    )


def comment_row(comment: Comment) -> dict:
    return {
        "id": str(comment.id),
        "body": comment.body,
        "author": comment.author_name,
        "author_id": str(comment.author_id) if comment.author_id else None,
        "created_at": comment.created_at.isoformat(),
        "edited_at": comment.edited_at.isoformat() if comment.edited_at else None,
    }


def delete_comment(db: DbSession, *, comment: Comment, actor, actor_name: str) -> None:
    excerpt = comment.body[:120]
    comment.deleted_at = datetime.now(timezone.utc)
    db.flush()
    record_activity(
        db,
        team_id=comment.team_id,
        actor=actor,
        actor_name=actor_name,
        verb="comment.deleted",
        target_type=comment.target_type,
        target_id=comment.target_id,
        payload={"target_label": f"the {comment.target_type}", "excerpt": excerpt},
    )


def get_comment(db: DbSession, *, team_id: uuid.UUID, comment_id: uuid.UUID) -> Comment:
    comment = db.execute(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.team_id == team_id,
            Comment.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if comment is None:
        raise NotFoundError("That comment does not exist.")
    return comment


def ensure_comment_author(actor, comment: Comment) -> None:
    if comment.author_id is None or comment.author_id != actor.user_id:
        raise PermissionDeniedError("You can only change your own comment.")


def guest_or_user_name(
    db: DbSession, *, user_id: uuid.UUID | None, guest_id: uuid.UUID | None
) -> str:
    if user_id is not None:
        return user_name(db, user_id)
    if guest_id is not None:
        guest = db.get(Guest, guest_id)
        return guest.display_name if guest else "A guest"
    return "Someone"
