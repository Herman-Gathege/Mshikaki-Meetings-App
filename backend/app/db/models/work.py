"""Ideas, decisions, projects, tasks and blockers - the work that outlives meetings."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDelete, Timestamps, UuidPk
from app.domain.enums import (
    IdeaStatus,
    ProjectStatus,
    TaskPriority,
    TaskStatus,
)


class Idea(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "ideas"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'discussing', 'accepted', 'parked', 'rejected', 'converted')",
            name="status_valid",
        ),
        Index("ix_ideas_team_status", "team_id", "status"),
        Index("ix_ideas_session", "session_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agenda_items.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Guests can capture ideas too; the name is kept for the record.
    author_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=IdeaStatus.NEW.value, nullable=False)
    converted_to_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    converted_to_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    tags: Mapped[list[IdeaTag]] = relationship(back_populates="idea", cascade="all, delete-orphan")


class IdeaTag(UuidPk, Base):
    __tablename__ = "idea_tags"
    __table_args__ = (UniqueConstraint("idea_id", "tag", name="uq_idea_tags_idea_tag"),)

    idea_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(60), nullable=False)

    idea: Mapped[Idea] = relationship(back_populates="tags")


class Decision(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(
            "session_id IS NOT NULL OR standalone_reason IS NOT NULL",
            name="decision_has_context",
        ),
        Index("ix_decisions_team", "team_id", "decided_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    idea_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True
    )
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agenda_items.id", ondelete="SET NULL"), nullable=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_by_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True
    )
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True
    )
    standalone_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Project(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'done')", name="status_valid"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=ProjectStatus.ACTIVE.value, nullable=False
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Task(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('backlog', 'in_progress', 'blocked', 'done', 'cancelled')",
            name="status_valid",
        ),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="priority_valid"),
        # The durable rule: nothing but a backlog task may be unowned.
        CheckConstraint(
            "owner_id IS NOT NULL OR status IN ('backlog', 'cancelled')",
            name="owner_required_outside_backlog",
        ),
        Index("ix_tasks_team_status_due", "team_id", "status", "due_date"),
        Index("ix_tasks_owner_status", "owner_id", "status"),
        Index("ix_tasks_session", "session_id"),
        Index("ix_tasks_project", "project_id"),
        Index("ix_tasks_origin", "idea_id", "decision_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    # Origin links. Permanent: they are how we answer "why does this exist?".
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    idea_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True
    )
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True
    )
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agenda_items.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=TaskStatus.BACKLOG.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(16), default=TaskPriority.NORMAL.value, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    collaborators: Mapped[list[TaskCollaborator]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    blockers: Mapped[list[Blocker]] = relationship(back_populates="task")


class TaskCollaborator(UuidPk, Base):
    __tablename__ = "task_collaborators"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_collaborators_task_user"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    task: Mapped[Task] = relationship(back_populates="collaborators")


class Blocker(UuidPk, Timestamps, Base):
    __tablename__ = "blockers"
    __table_args__ = (
        CheckConstraint("task_id IS NOT NULL OR idea_id IS NOT NULL", name="blocker_has_a_target"),
        Index("ix_blockers_open", "team_id", "resolved_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    idea_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ideas.id", ondelete="CASCADE"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    raised_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    raised_by_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    raised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task | None] = relationship(back_populates="blockers")

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None
