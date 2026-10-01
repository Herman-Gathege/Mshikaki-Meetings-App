"""Keep the room on the same Run Mode stage

The facilitator drives the meeting. Rather than every client guessing from its own
taps, the authoritative stage lives on the session, so a participant who joins
late converges on the same screen without websockets or a second realtime system.

Revision ID: 0004_run_mode_stage
Revises: 0003_append_only
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_run_mode_stage"
down_revision: str | None = "0003_append_only"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("run_mode_stage", sa.String(length=16), nullable=True))
    op.add_column(
        "sessions",
        sa.Column("run_mode_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "run_mode_stage_valid",
        "sessions",
        "run_mode_stage IS NULL OR run_mode_stage IN ('play', 'capture', 'decide', 'assign', 'close')",
    )


def downgrade() -> None:
    op.drop_constraint("run_mode_stage_valid", "sessions", type_="check")
    op.drop_column("sessions", "run_mode_updated_at")
    op.drop_column("sessions", "run_mode_stage")
