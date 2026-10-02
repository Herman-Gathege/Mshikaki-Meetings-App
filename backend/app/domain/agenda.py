"""Agenda rules: where the room is, and what an item ended as.

The meeting walks a numbered list, one item at a time, and the facilitator
decides when to move on. Everything here is a pure function so the arithmetic
of "2 of 5" and the vocabulary of outcomes can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass

# What the room did with an item. Deliberately small: the UI shows these as
# plain sentences, and the record keeps one word.
ACCOMPLISHED = "accomplished"
PENDING = "pending"
ASSIGNED = "assigned"
NOTHING = "none"

OUTCOMES: tuple[str, ...] = (ACCOMPLISHED, PENDING, ASSIGNED, NOTHING)

OUTCOME_LABELS: dict[str, str] = {
    ACCOMPLISHED: "Done with this",
    PENDING: "Still pending",
    ASSIGNED: "Someone is taking this",
    NOTHING: "Nothing decided",
}


class UnknownOutcome(Exception):
    def __init__(self, outcome: str) -> None:
        super().__init__(f"'{outcome}' is not an agenda outcome")
        self.outcome = outcome


def is_outcome(value: str) -> bool:
    return value in OUTCOMES


def ensure_outcome(value: str) -> str:
    if not is_outcome(value):
        raise UnknownOutcome(value)
    return value


@dataclass(frozen=True)
class Progress:
    """Where the room is in the list, counted the way a person would say it."""

    position: int  # 1-based, 0 when the agenda is empty
    total: int
    remaining: int

    @property
    def is_last(self) -> bool:
        return self.total > 0 and self.position >= self.total


def progress(index: int, total: int) -> Progress:
    """Turn a zero-based index into 'Agenda 2 of 5'."""
    if total <= 0:
        return Progress(position=0, total=0, remaining=0)
    if index < 0:
        # No item is current: the agenda is finished, not resting on the first.
        return Progress(position=0, total=total, remaining=total)
    bounded = min(max(index, 0), total - 1)
    position = bounded + 1
    return Progress(position=position, total=total, remaining=total - position)


def next_index(index: int, total: int) -> int | None:
    """The index after this one, or None when the agenda is finished."""
    if total <= 0:
        return None
    following = index + 1
    return following if following < total else None
