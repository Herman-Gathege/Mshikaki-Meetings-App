"""XP as a ledger, seasons, achievements and the (mostly unused) notification table."""

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import Timestamps, UuidPk
from app.domain.enums import SeasonStatus


class XpRuleModel(UuidPk, Timestamps, Base):
    __tablename__ = "xp_rules"

    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_per_session: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diminishing_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Season(UuidPk, Timestamps, Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("status IN ('upcoming', 'active', 'closed')", name="status_valid"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=SeasonStatus.ACTIVE.value, nullable=False
    )


class XpEvent(UuidPk, Base):
    """Append-only. A person's score is the sum of their events, never a counter."""

    __tablename__ = "xp_events"
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL OR guest_id IS NOT NULL", name="xp_has_a_subject"),
        Index("ix_xp_events_leaderboard", "team_id", "season_id", "user_id"),
        Index("ix_xp_events_subject_time", "user_id", "occurred_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=True
    )
    subject_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    awarded_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    season_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class Achievement(UuidPk, Timestamps, Base):
    __tablename__ = "achievements"

    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str] = mapped_column(String(8), default="🏆", nullable=False)
    criteria: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), default="common", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AchievementAward(UuidPk, Base):
    __tablename__ = "achievement_awards"
    __table_args__ = (Index("ix_achievement_awards_subject", "team_id", "user_id"),)

    achievement_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=True
    )
    season_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    awarded_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Notification(UuidPk, Base):
    """Reserved for the single daily digest. Nothing else writes here in MVP 1."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
