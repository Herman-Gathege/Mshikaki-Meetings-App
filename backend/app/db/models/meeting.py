"""Sessions: the meeting, who was in it, and the agenda."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDelete, Timestamps, UuidPk
from app.domain.enums import ParticipantRole, SessionStatus


class Session(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'active', 'paused', 'completed', 'cancelled')",
            name="status_valid",
        ),
        UniqueConstraint("team_id", "sequence_no", name="uq_sessions_team_sequence"),
        # One live meeting at a time, enforced by the database rather than by hope.
        Index(
            "uq_sessions_one_active_per_team",
            "team_id",
            unique=True,
            postgresql_where=text("status = 'active' AND deleted_at IS NULL"),
        ),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=SessionStatus.PLANNED.value, nullable=False, index=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    facilitator_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Nairobi", nullable=False)
    summary_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    participants: Mapped[list[SessionParticipant]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    agenda_items: Mapped[list[AgendaItem]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AgendaItem.position"
    )


class SessionParticipant(UuidPk, Timestamps, Base):
    __tablename__ = "session_participants"
    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR guest_id IS NOT NULL",
            name="session_participant_is_a_person",
        ),
        UniqueConstraint("session_id", "user_id", name="uq_session_your_participant"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=True
    )
    role: Mapped[str] = mapped_column(
        String(16), default=ParticipantRole.PARTICIPANT.value, nullable=False
    )
    attended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[Session] = relationship(back_populates="participants")


class AgendaItem(UuidPk, Timestamps, Base):
    __tablename__ = "agenda_items"

    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    timebox_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    covered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[Session] = relationship(back_populates="agenda_items")
