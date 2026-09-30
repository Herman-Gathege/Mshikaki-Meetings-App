"""Bragging rights, calculated honestly.

XP is a ledger of events, never a running total on a user row. This module owns
the arithmetic: how much a single award is worth once caps, diminishing returns
and the facilitator discount are applied.

Caps are **counts of awards**, not points: `max_per_day=3` means at most three XP
events from that rule per day. Counting awards is harder to game than counting
points, and it is trivial to explain to a person who asks why they stopped
earning.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class XpRule:
    key: str
    label: str
    amount: int
    max_per_session: int | None = None
    max_per_day: int | None = None
    max_per_week: int | None = None
    # After this many occurrences in the window, each further award halves.
    diminishing_after: int | None = None


DEFAULT_RULES: dict[str, XpRule] = {
    "attend_session": XpRule("attend_session", "Showed up", 5, max_per_session=1),
    "game_played": XpRule("game_played", "Played a game", 5, max_per_session=3),
    "game_won": XpRule("game_won", "Won a game", 15, max_per_session=2),
    "game_placed": XpRule("game_placed", "Placed in a game", 8, max_per_session=2),
    "idea_submitted": XpRule(
        "idea_submitted", "Idea submitted", 10, max_per_day=3, diminishing_after=1
    ),
    "idea_accepted": XpRule("idea_accepted", "Idea accepted", 20, max_per_week=5),
    "decision_recorded": XpRule(
        "decision_recorded", "Decision recorded", 10, max_per_session=5, diminishing_after=2
    ),
    "task_completed": XpRule(
        "task_completed", "Task completed", 15, max_per_week=5, diminishing_after=2
    ),
    "blocker_resolved": XpRule("blocker_resolved", "Blocker resolved", 25, max_per_week=4),
    "early_bird": XpRule("early_bird", "First to arrive", 3, max_per_session=1),
    "login": XpRule("login", "Signed in", 0, max_per_day=0),
}

# Actions that are structural - pressing a button the facilitator has to press.
# Who holds the pen should not decide who wins the season.
FACILITATOR_DISCOUNTED = frozenset({"decision_recorded", "task_completed"})
FACILITATOR_WEIGHT = 0.5

# Rules that never award anything, listed explicitly so the intent is reviewable.
ZERO_RULES = frozenset({"login"})


def rule(key: str) -> XpRule:
    try:
        return DEFAULT_RULES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown XP rule '{key}'") from exc


def award_amount(
    rule_key: str,
    *,
    awards_this_session: int = 0,
    awards_today: int = 0,
    awards_this_week: int = 0,
    occurrence_index: int = 0,
) -> int:
    """What one more award is worth right now. Zero means the cap has been hit."""
    spec = rule(rule_key)
    if spec.amount <= 0:
        return 0
    if spec.max_per_session is not None and awards_this_session >= spec.max_per_session:
        return 0
    if spec.max_per_day is not None and awards_today >= spec.max_per_day:
        return 0
    if spec.max_per_week is not None and awards_this_week >= spec.max_per_week:
        return 0

    amount = spec.amount
    if spec.diminishing_after is not None and occurrence_index >= spec.diminishing_after:
        steps = occurrence_index - spec.diminishing_after + 1
        amount = max(1, amount >> steps)
    return amount


def apply_facilitator_weight(rule_key: str, amount: int, *, facilitator_created_it: bool) -> int:
    if not facilitator_created_it or rule_key not in FACILITATOR_DISCOUNTED:
        return amount
    return max(1, int(amount * FACILITATOR_WEIGHT))


def idempotency_key(
    reason_key: str,
    source_type: str,
    source_id: uuid.UUID | str,
    subject_id: uuid.UUID | str,
) -> str:
    """Stable key so replaying a job cannot double-award.

    Hashed to keep the column a predictable length and to avoid leaking ids.
    """
    raw = f"{reason_key}|{source_type}|{source_id}|{subject_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def season_name(index: int) -> str:
    return f"Kika Season {index}"
