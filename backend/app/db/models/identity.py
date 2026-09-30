"""Organisation, team, people and access."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDelete, Timestamps, UuidPk
from app.domain.enums import MembershipStatus, TeamRole


class Organization(UuidPk, Timestamps, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    teams: Mapped[list[Team]] = relationship(back_populates="organization")


class Team(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "teams"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Nairobi", nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="teams")
    memberships: Mapped[list[Membership]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class User(UuidPk, Timestamps, SoftDelete, Base):
    """Email is stored lower-cased by the service layer; uniqueness is exact."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Nairobi", nullable=False)
    # Private: opted-out people simply do not appear in standings, unexplained.
    leaderboard_opt_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[list[Membership]] = relationship(back_populates="user")

    @property
    def first_name(self) -> str:
        return self.display_name.split(" ")[0]


class Membership(UuidPk, Timestamps, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "team_id", name="uq_memberships_user_team"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), default=TeamRole.MEMBER.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=MembershipStatus.ACTIVE.value, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    team: Mapped[Team] = relationship(back_populates="memberships")


class Invite(UuidPk, Timestamps, Base):
    __tablename__ = "invites"

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(32), default=TeamRole.MEMBER.value, nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Guest(UuidPk, Timestamps, Base):
    """A participant without an account. Claimable later, never rewritten."""

    __tablename__ = "guests"

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    linked_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AuthSession(UuidPk, Timestamps, Base):
    """A login. Named auth_sessions so nobody confuses it with a meeting."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
