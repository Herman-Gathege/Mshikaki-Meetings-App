"""Task and blocker rules.

The two are coupled on purpose: a task in `blocked` and its open blocker records
are one fact expressed twice, and they must never disagree.
"""

from __future__ import annotations

from app.domain.enums import TaskPriority, TaskStatus

TRANSITIONS: dict[str, frozenset[str]] = {
    TaskStatus.BACKLOG.value: frozenset({TaskStatus.IN_PROGRESS.value, TaskStatus.CANCELLED.value}),
    TaskStatus.IN_PROGRESS.value: frozenset(
        {
            TaskStatus.BLOCKED.value,
            TaskStatus.DONE.value,
            TaskStatus.CANCELLED.value,
            TaskStatus.BACKLOG.value,
        }
    ),
    TaskStatus.BLOCKED.value: frozenset({TaskStatus.IN_PROGRESS.value, TaskStatus.CANCELLED.value}),
    TaskStatus.DONE.value: frozenset({TaskStatus.IN_PROGRESS.value}),
    TaskStatus.CANCELLED.value: frozenset({TaskStatus.BACKLOG.value}),
}

# A task may be unowned only while it is sitting in the backlog.
STATUSES_REQUIRING_OWNER = frozenset(
    {TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value, TaskStatus.DONE.value}
)

TERMINAL_STATUSES = frozenset({TaskStatus.DONE.value, TaskStatus.CANCELLED.value})

PRIORITY_WEIGHT: dict[str, int] = {
    TaskPriority.LOW.value: 1,
    TaskPriority.NORMAL.value: 2,
    TaskPriority.HIGH.value: 3,
    TaskPriority.URGENT.value: 4,
}


class InvalidTaskTransition(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot move a task from '{current}' to '{target}'")
        self.current = current
        self.target = target


class OwnerRequired(Exception):
    def __init__(self, status: str) -> None:
        super().__init__(f"A task in '{status}' must have an owner")
        self.status = status


class BlockerRequired(Exception):
    def __init__(self, message: str = 'A task in "blocked" must have an open blocker') -> None:
        super().__init__(message)


def can_transition(current: str, target: str) -> bool:
    if current == target:
        return True
    return target in TRANSITIONS.get(current, frozenset())


def ensure_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise InvalidTaskTransition(current, target)


def requires_owner(status: str) -> bool:
    return status in STATUSES_REQUIRING_OWNER


def ensure_owner(status: str, owner_id: object | None) -> None:
    if requires_owner(status) and owner_id is None:
        raise OwnerRequired(status)


def ensure_blocker_state(status: str, has_open_blocker: bool) -> None:
    """Called on every status change and blocker change."""
    if status == TaskStatus.BLOCKED.value and not has_open_blocker:
        raise BlockerRequired()
    if status != TaskStatus.BLOCKED.value and has_open_blocker:
        raise BlockerRequired(
            "The task has an open blocker but is not in 'blocked'; resolve the blocker first"
        )


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


def completed_on_time(due_date: object | None, completed_at: object | None) -> bool:
    """Used by the 'Deadline Destroyer' achievement. Dates are date objects."""
    if due_date is None or completed_at is None:
        return False
    return completed_at.date() <= due_date  # type: ignore[attr-defined]
