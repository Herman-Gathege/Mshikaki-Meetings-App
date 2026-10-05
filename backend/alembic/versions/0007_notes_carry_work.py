"""A note can be given to somebody and marked where it got to

The user test asked for notes they can edit, assign to a joiner, and mark
pending, done or backlog. A note stays a note: this adds an owner and a small
state to the table that already holds the body.

Revision ID: 0007_notes_carry_work
Revises: 0006_agenda_backbone
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_notes_carry_work"
down_revision: str | None = "0006_agenda_backbone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("assignee_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_notes_assignee_id_users"),
        "notes",
        "users",
        ["assignee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "notes",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
    )
    op.add_column(
        "notes",
        sa.Column(
            "mentions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_check_constraint(
        "status_valid",
        "notes",
        "status IN ('open', 'pending', 'done', 'backlog')",
    )


def downgrade() -> None:
    op.drop_column("notes", "mentions")
    op.drop_constraint("status_valid", "notes", type_="check")
    op.drop_column("notes", "status")
    op.drop_constraint(op.f("fk_notes_assignee_id_users"), "notes", type_="foreignkey")
    op.drop_column("notes", "assignee_id")
