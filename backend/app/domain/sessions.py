"""Session lifecycle rules."""

from __future__ import annotations

from app.domain.enums import SessionStatus

TRANSITIONS: dict[str, frozenset[str]] = {
    SessionStatus.PLANNED.value: frozenset(
        {SessionStatus.ACTIVE.value, SessionStatus.CANCELLED.value}
    ),
    SessionStatus.ACTIVE.value: frozenset(
        {SessionStatus.PAUSED.value, SessionStatus.COMPLETED.value, SessionStatus.CANCELLED.value}
    ),
    SessionStatus.PAUSED.value: frozenset(
        {SessionStatus.ACTIVE.value, SessionStatus.COMPLETED.value, SessionStatus.CANCELLED.value}
    ),
    # Reopening a closed meeting happens in real life; it is audited and it marks
    # the frozen summary stale.
    SessionStatus.COMPLETED.value: frozenset({SessionStatus.ACTIVE.value}),
    SessionStatus.CANCELLED.value: frozenset({SessionStatus.PLANNED.value}),
}

OPEN_STATUSES = frozenset({SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value})
LIVE_STATUSES = frozenset({SessionStatus.ACTIVE.value})


class InvalidSessionTransition(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot move a session from '{current}' to '{target}'")
        self.current = current
        self.target = target


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def ensure_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise InvalidSessionTransition(current, target)


def is_open(status: str) -> bool:
    return status in OPEN_STATUSES


def is_live(status: str) -> bool:
    return status in LIVE_STATUSES


def next_sequence_number(existing: list[int]) -> int:
    """'Weekly Session #12' without a counter column to keep in sync."""
    return (max(existing) + 1) if existing else 1


def default_title(team_name: str, sequence_no: int) -> str:
    return f"{team_name} Session #{sequence_no}"
