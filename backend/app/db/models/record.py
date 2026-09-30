"""The record: activity and comments. Append-only by policy and by grant."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDelete, UuidPk
from app.domain.enums import COMMENT_TARGETS, ActivityVisibility, ActorType


class Activity(UuidPk, Base):
    """One thing that happened. Never updated, never deleted.

    `actor_name` is denormalised on purpose: the trail must stay readable after a
    person is renamed, removed, or anonymised for a privacy request.
    """

    __tablename__ = "activity"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'guest', 'system')", name="actor_type_valid"),
        Index("ix_activity_team_occurred", "team_id", "occurred_at"),
        Index("ix_activity_session_occurred", "session_id", "occurred_at"),
        Index("ix_activity_target", "target_type", "target_id", "occurred_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(16), default=ActorType.USER.value, nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    verb: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), default="web", nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(16), default=ActivityVisibility.TEAM.value, nullable=False
    )


class Comment(UuidPk, SoftDelete, Base):
    """One flat thread per target. No nesting in MVP 1."""

    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('idea', 'decision', 'task', 'blocker', 'session')",
            name="comment_target_valid",
        ),
        Index("ix_comments_target", "target_type", "target_id", "created_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def valid_targets(self) -> frozenset[str]:
        return COMMENT_TARGETS
