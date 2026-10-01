"""One question, live for the whole room

The host screen and every phone need the same clock. Rather than trusting each
browser's own timer, the play carries the moment the current question went live
and the moment its answer was revealed, and a player's answer is stored once.

Revision ID: 0005_live_questions
Revises: 0004_run_mode_stage
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_live_questions"
down_revision: str | None = "0004_run_mode_stage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_plays",
        sa.Column("question_seconds", sa.Integer(), nullable=False, server_default="20"),
    )
    op.add_column(
        "game_plays", sa.Column("question_started_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "game_plays", sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "game_answers",
        sa.Column("game_play_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("guest_id", sa.UUID(), nullable=True),
        sa.Column("player_name", sa.String(length=120), nullable=False),
        sa.Column("choice", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR guest_id IS NOT NULL",
            name=op.f("ck_game_answers_answer_has_a_player"),
        ),
        sa.ForeignKeyConstraint(
            ["game_play_id"],
            ["game_plays.id"],
            name=op.f("fk_game_answers_game_play_id_game_plays"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["guest_id"],
            ["guests.id"],
            name=op.f("fk_game_answers_guest_id_guests"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["game_questions.id"],
            name=op.f("fk_game_answers_question_id_game_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_game_answers_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_answers")),
    )
    op.create_index(op.f("ix_game_answers_play"), "game_answers", ["game_play_id"], unique=False)
    op.create_index(
        "uq_game_answers_play_question_user",
        "game_answers",
        ["game_play_id", "question_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_game_answers_play_question_guest",
        "game_answers",
        ["game_play_id", "question_id", "guest_id"],
        unique=True,
        postgresql_where=sa.text("guest_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_game_answers_play_question_guest", table_name="game_answers")
    op.drop_index("uq_game_answers_play_question_user", table_name="game_answers")
    op.drop_index(op.f("ix_game_answers_play"), table_name="game_answers")
    op.drop_table("game_answers")
    op.drop_column("game_plays", "revealed_at")
    op.drop_column("game_plays", "question_started_at")
    op.drop_column("game_plays", "question_seconds")
