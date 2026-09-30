"""Small, shared column sets.

Three mixins, no more: an id, timestamps, and soft delete. Anything richer belongs
in the model that needs it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UuidPk:
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=utcnow,
        nullable=False,
    )


class SoftDelete:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class TeamScoped:
    """Every domain table carries the team. Enforced in review and by tests."""

    @staticmethod
    def team_fk() -> Mapped[uuid.UUID]:
        return mapped_column(
            PgUUID(as_uuid=True),
            ForeignKey("teams.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
