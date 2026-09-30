"""initial

Establishes the migration chain. The first real tables arrive in Phase 1.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-30
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
