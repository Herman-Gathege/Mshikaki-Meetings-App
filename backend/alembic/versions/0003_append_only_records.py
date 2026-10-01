"""Make the record append-only in the database, not just in the code

The product promises that the activity trail and the XP ledger cannot be edited
or deleted. Code review is not enforcement: a migration, a script, or a stray
`session.execute` could still rewrite history. These triggers make it impossible
for any role, including the application's own.

`achievement_awards` is deliberately excluded. Revoking an award sets
`revoked_at` by design, and that revocation is itself recorded in `activity`.

Revision ID: 0003_append_only
Revises: 143b9ac0f90f
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_append_only"
down_revision: str | None = "143b9ac0f90f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APPEND_ONLY_TABLES = ("activity", "xp_events")


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION mshikaki_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'The Mshikaki record is append-only: % is not allowed on %.%',
                TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION mshikaki_reject_mutation();"
        )


def downgrade() -> None:
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table};")
    op.execute("DROP FUNCTION IF EXISTS mshikaki_reject_mutation();")
