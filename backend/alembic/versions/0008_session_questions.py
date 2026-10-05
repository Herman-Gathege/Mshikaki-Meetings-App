"""Questions the room writes during the meeting

The game library is the team's; this is one meeting's own questions. Anybody in
the room can suggest one, everybody sees them, and the accepted ones can be
played without touching a content file.

Revision ID: 0008_session_questions
Revises: 0007_notes_carry_work
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_session_questions"
down_revision: str | None = "0007_notes_carry_work"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_questions",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("agenda_item_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("author_name", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="suggested"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('suggested', 'accepted', 'used', 'rejected')",
            name=op.f("ck_session_questions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["agenda_item_id"],
            ["agenda_items.id"],
            name=op.f("fk_session_questions_agenda_item_id_agenda_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_session_questions_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name=op.f("fk_session_questions_session_id_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_session_questions_team_id_teams"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_questions")),
    )
    op.create_index(
        op.f("ix_session_questions_session"), "session_questions", ["session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_questions_session"), table_name="session_questions")
    op.drop_table("session_questions")
