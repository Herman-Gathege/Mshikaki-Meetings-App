"""Game content and play. Content is data; behaviour is code."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
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
from app.domain.enums import GameFamily, GamePlayStatus


class GameDefinition(UuidPk, Timestamps, Base):
    __tablename__ = "game_definitions"
    __table_args__ = (
        CheckConstraint(
            "family IN ('prompt_deck', 'host_quiz', 'host_scored')", name="family_valid"
        ),
    )

    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    family: Mapped[str] = mapped_column(
        String(32), default=GameFamily.PROMPT_DECK.value, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_schema: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    min_players: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    energy: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    how_to_play: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ContentPack(UuidPk, Timestamps, SoftDelete, Base):
    __tablename__ = "content_packs"

    game_definition_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("game_definitions.key", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    # Licensing is not optional: a pack without a declared licence does not ship.
    license: Mapped[str] = mapped_column(String(120), nullable=False)
    attribution: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    questions: Mapped[list[GameQuestion]] = relationship(
        back_populates="pack", cascade="all, delete-orphan", order_by="GameQuestion.position"
    )


class GameQuestion(UuidPk, Timestamps, Base):
    __tablename__ = "game_questions"
    __table_args__ = (UniqueConstraint("content_pack_id", "position", name="uq_question_position"),)

    content_pack_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("content_packs.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    choices: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    pack: Mapped[ContentPack] = relationship(back_populates="questions")


class GamePlay(UuidPk, Timestamps, Base):
    __tablename__ = "game_plays"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'finished', 'abandoned')", name="status_valid"
        ),
        Index("ix_game_plays_session", "session_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    game_definition_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_definitions.key", ondelete="RESTRICT"), nullable=False
    )
    content_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("content_packs.id", ondelete="SET NULL"), nullable=True
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=GamePlayStatus.RUNNING.value, nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    question_order: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The live window for the current question. `question_started_at` is what the
    # whole room counts down from, and `revealed_at` closes it. Both are on the
    # play, not in a browser, so every phone agrees on the clock.
    question_seconds: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    question_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scores: Mapped[list[GameScore]] = relationship(
        back_populates="play", cascade="all, delete-orphan"
    )
    answers: Mapped[list[GameAnswer]] = relationship(
        back_populates="play", cascade="all, delete-orphan"
    )


class GameScore(UuidPk, Timestamps, Base):
    __tablename__ = "game_scores"
    __table_args__ = (
        CheckConstraint("source IN ('auto', 'host')", name="source_valid"),
        CheckConstraint("user_id IS NOT NULL OR guest_id IS NOT NULL", name="score_has_a_player"),
    )

    game_play_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("game_plays.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True
    )
    player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(8), default="host", nullable=False)
    adjusted_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    adjustment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    play: Mapped[GamePlay] = relationship(back_populates="scores")


class GameAnswer(UuidPk, Timestamps, Base):
    """One player's answer to one question. Given once, then locked in.

    Answers are game data, not work data: they are deliberately not written to
    the activity trail one by one. The reveal writes a single summary line.
    """

    __tablename__ = "game_answers"
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL OR guest_id IS NOT NULL", name="answer_has_a_player"),
        Index("ix_game_answers_play", "game_play_id"),
        Index(
            "uq_game_answers_play_question_user",
            "game_play_id",
            "question_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_game_answers_play_question_guest",
            "game_play_id",
            "question_id",
            "guest_id",
            unique=True,
            postgresql_where=text("guest_id IS NOT NULL"),
        ),
    )

    game_play_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("game_plays.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("game_questions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True
    )
    player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    choice: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    play: Mapped[GamePlay] = relationship(back_populates="answers")

class SessionQuestion(UuidPk, Timestamps, SoftDelete, Base):
    """A question somebody in the room thought of, during the meeting.

    The game library belongs to the team; this belongs to one meeting. The room
    writes questions as they occur to them, everybody sees them, and the ones
    that are accepted can be played straight away instead of waiting for
    somebody to edit a content file.
    """

    __tablename__ = "session_questions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('suggested', 'accepted', 'used', 'rejected')",
            name="status_valid",
        ),
        Index("ix_session_questions_session", "session_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agenda_items.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author_name: Mapped[str] = mapped_column(String(120), default="Someone", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="suggested", nullable=False)
