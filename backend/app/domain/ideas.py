"""Idea status rules.

The point worth protecting: parked and rejected are respectable endings. Not every
idea becomes work, and the product must not shame people for that.
"""

from __future__ import annotations

from app.domain.enums import IdeaStatus

TRANSITIONS: dict[str, frozenset[str]] = {
    IdeaStatus.NEW.value: frozenset(
        {
            IdeaStatus.DISCUSSING.value,
            IdeaStatus.ACCEPTED.value,
            IdeaStatus.PARKED.value,
            IdeaStatus.REJECTED.value,
        }
    ),
    IdeaStatus.DISCUSSING.value: frozenset(
        {
            IdeaStatus.ACCEPTED.value,
            IdeaStatus.PARKED.value,
            IdeaStatus.REJECTED.value,
            IdeaStatus.NEW.value,
        }
    ),
    IdeaStatus.PARKED.value: frozenset(
        {IdeaStatus.DISCUSSING.value, IdeaStatus.REJECTED.value, IdeaStatus.ACCEPTED.value}
    ),
    IdeaStatus.ACCEPTED.value: frozenset(
        {IdeaStatus.CONVERTED.value, IdeaStatus.PARKED.value, IdeaStatus.DISCUSSING.value}
    ),
    IdeaStatus.REJECTED.value: frozenset({IdeaStatus.DISCUSSING.value}),
    # Converted ideas stay readable and point at what they became.
    IdeaStatus.CONVERTED.value: frozenset(),
}

CONVERTIBLE = frozenset(
    {
        IdeaStatus.NEW.value,
        IdeaStatus.DISCUSSING.value,
        IdeaStatus.ACCEPTED.value,
        IdeaStatus.PARKED.value,
    }
)


class InvalidIdeaTransition(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot move an idea from '{current}' to '{target}'")
        self.current = current
        self.target = target


def can_transition(current: str, target: str) -> bool:
    if current == target:
        return True
    return target in TRANSITIONS.get(current, frozenset())


def ensure_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise InvalidIdeaTransition(current, target)


def is_converted(status: str) -> bool:
    return status == IdeaStatus.CONVERTED.value


def can_convert(status: str) -> bool:
    return status in CONVERTIBLE
