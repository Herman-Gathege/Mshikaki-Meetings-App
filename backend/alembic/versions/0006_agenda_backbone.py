"""The agenda carries the meeting

The facilitator moves the room through the agenda item by item, so the session
remembers which item is current. Ideas, decisions and tasks remember the item
they came from, and notes get their own small table so a meeting can keep a
scratchpad that is neither an idea nor a task.

Revision ID: 0006_agenda_backbone
Revises: 0005_live_questions
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_agenda_backbone"
down_revision: str | None = "0005_live_questions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The room can now sit on the agenda as well as the older per-topic screens.
    op.drop_constraint("run_mode_stage_valid", "sessions", type_="check")
    op.create_check_constraint(
        "run_mode_stage_valid",
        "sessions",
        "run_mode_stage IS NULL OR run_mode_stage IN "
        "('play', 'agenda', 'capture', 'decide', 'assign', 'close')",
    )

    # What the room did with an item, in one small word.
    op.add_column("agenda_items", sa.Column("outcome", sa.String(length=16), nullable=True))
    op.add_column(
        "agenda_items", sa.Column("outcome_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "outcome_valid",
        "agenda_items",
        "outcome IS NULL OR outcome IN ('accomplished', 'pending', 'assigned', 'none')",
    )

    # The item the room is on right now.
    op.add_column("sessions", sa.Column("current_agenda_item_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_sessions_current_agenda_item_id_agenda_items"),
        "sessions",
        "agenda_items",
        ["current_agenda_item_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Origin: which agenda item an idea, a decision or a task came from.
    for table in ("ideas", "decisions", "tasks"):
        op.add_column(table, sa.Column("agenda_item_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{table}_agenda_item_id_agenda_items"),
            table,
            "agenda_items",
            ["agenda_item_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(f"ix_{table}_agenda_item", table, ["agenda_item_id"], unique=False)

    # The meeting scratchpad.
    op.create_table(
        "notes",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("agenda_item_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("author_name", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["agenda_item_id"],
            ["agenda_items.id"],
            name=op.f("fk_notes_agenda_item_id_agenda_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_notes_author_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name=op.f("fk_notes_session_id_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_notes_team_id_teams"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
    )
    op.create_index(op.f("ix_notes_session"), "notes", ["session_id"], unique=False)
    op.create_index(op.f("ix_notes_agenda_item"), "notes", ["agenda_item_id"], unique=False)


def downgrade() -> None:
    op.drop_constraint("run_mode_stage_valid", "sessions", type_="check")
    op.create_check_constraint(
        "run_mode_stage_valid",
        "sessions",
        "run_mode_stage IS NULL OR run_mode_stage IN "
        "('play', 'capture', 'decide', 'assign', 'close')",
    )
    op.drop_index(op.f("ix_notes_agenda_item"), table_name="notes")
    op.drop_index(op.f("ix_notes_session"), table_name="notes")
    op.drop_table("notes")
    for table in ("ideas", "decisions", "tasks"):
        op.drop_index(f"ix_{table}_agenda_item", table_name=table)
        op.drop_constraint(
            op.f(f"fk_{table}_agenda_item_id_agenda_items"), table, type_="foreignkey"
        )
        op.drop_column(table, "agenda_item_id")
    op.drop_constraint(
        op.f("fk_sessions_current_agenda_item_id_agenda_items"), "sessions", type_="foreignkey"
    )
    op.drop_column("sessions", "current_agenda_item_id")
    op.drop_constraint("outcome_valid", "agenda_items", type_="check")
    op.drop_column("agenda_items", "outcome_at")
    op.drop_column("agenda_items", "outcome")
