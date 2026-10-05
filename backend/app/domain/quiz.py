"""The rules of a live question, with no database and no framework.

Deliberately Kahoot-shaped: one question is live for the whole room at the same
moment, a player answers once and is then locked in, and a correct answer is
worth a little more when it was quick. Nobody's answer shortens anybody else's
clock - the window belongs to the question, not to a player.

Everything here is a pure function, so the rules can be tested without a
database and cannot drift between the host screen, the player screen and the
score the server writes.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

DEFAULT_QUESTION_SECONDS = 20
BASE_POINTS = 10
# A quick right answer is worth more, but not so much that a slow reader is
# playing a different game. Half the clock is "quick".
SPEED_BONUS = 5


def answer_is_correct(choice: str | None, answer: str | None) -> bool:
    """Whether a chosen option matches the question's answer.

    The answer line may carry a note ("Nairobi - the capital"), so an option that
    matches the part before the dash counts.
    """
    if not choice or not answer:
        return False
    clean = answer.strip().lower()
    picked = choice.strip().lower()
    if not clean or not picked:
        return False
    return clean == picked or clean.startswith(picked) or picked.startswith(clean.split(" - ")[0])


def seconds_left(started_at: datetime | None, limit: int, now: datetime) -> int:
    """How long the room has left. The server owns this number, not the browser."""
    if started_at is None:
        return limit
    remaining = (started_at + timedelta(seconds=limit) - now).total_seconds()
    if remaining <= 0:
        return 0
    return math.ceil(remaining)


def is_accepting_answers(
    *,
    started_at: datetime | None,
    limit: int,
    revealed_at: datetime | None,
    now: datetime,
) -> bool:
    if started_at is None or revealed_at is not None:
        return False
    return seconds_left(started_at, limit, now) > 0


def points_for(*, correct: bool, elapsed_seconds: float, limit: int) -> int:
    """What one answer is worth. Wrong answers score nothing, as in Kahoot."""
    if not correct:
        return 0
    if limit > 0 and elapsed_seconds <= limit / 2:
        return BASE_POINTS + SPEED_BONUS
    return BASE_POINTS


def round_winners(answers: list[dict]) -> list[str]:
    """Who won the round, decided the same way every time.

    Most points that question, and because points already carry the speed bonus,
    that also settles a tie between two right answers. A round where nobody was
    right has no winner, which is a fact worth recording rather than inventing
    somebody to name.

    Each answer is {name, points, submitted_at}. Ties on both points and time
    name everybody involved.
    """
    scored = [row for row in answers if int(row.get("points") or 0) > 0]
    if not scored:
        return []

    best = max(int(row["points"]) for row in scored)
    leaders = [row for row in scored if int(row["points"]) == best]
    fastest = min(row["submitted_at"] for row in leaders)
    winners = [row for row in leaders if row["submitted_at"] == fastest]
    return sorted(str(row["name"]) for row in winners)
