"""The rules of a live question, tested without a database.

These are the promises the room feels: one clock, one answer each, and points
that do not depend on whose phone is faster.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from app.domain import quiz

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("choice", "answer"),
    [
        ("Nairobi", "Nairobi"),
        ("nairobi", "Nairobi"),
        ("Nairobi", "Nairobi - the capital"),
        ("Mombasa", "Mombasa - the port city"),
    ],
)
def test_a_right_answer_is_right(choice: str, answer: str) -> None:
    assert quiz.answer_is_correct(choice, answer) is True


@pytest.mark.parametrize(
    ("choice", "answer"),
    [
        ("Kisumu", "Nairobi"),
        (None, "Nairobi"),
        ("Nairobi", None),
        ("", ""),
    ],
)
def test_a_wrong_or_missing_answer_is_not_right(choice: str | None, answer: str | None) -> None:
    assert quiz.answer_is_correct(choice, answer) is False


def test_the_clock_belongs_to_the_question_not_the_player() -> None:
    """Everybody counts down from the same moment, whatever they are doing."""
    started = NOW
    assert quiz.seconds_left(started, 20, NOW) == 20
    assert quiz.seconds_left(started, 20, NOW + timedelta(seconds=4.5)) == 16
    assert quiz.seconds_left(started, 20, NOW + timedelta(seconds=19.2)) == 1
    assert quiz.seconds_left(started, 20, NOW + timedelta(seconds=20)) == 0
    assert quiz.seconds_left(started, 20, NOW + timedelta(seconds=99)) == 0


def test_answering_never_closes_anybody_elses_window() -> None:
    """The bug the room noticed: one answer must not stop the room's clock."""
    assert (
        quiz.is_accepting_answers(
            started_at=NOW, limit=20, revealed_at=None, now=NOW + timedelta(seconds=5)
        )
        is True
    )
    # Revealing, not answering, is what closes the question.
    assert (
        quiz.is_accepting_answers(
            started_at=NOW, limit=20, revealed_at=NOW + timedelta(seconds=5), now=NOW
        )
        is False
    )
    assert (
        quiz.is_accepting_answers(
            started_at=NOW, limit=20, revealed_at=None, now=NOW + timedelta(seconds=21)
        )
        is False
    )


def test_points_reward_a_quick_right_answer_and_nothing_else() -> None:
    assert quiz.points_for(correct=False, elapsed_seconds=1, limit=20) == 0
    assert quiz.points_for(correct=True, elapsed_seconds=1, limit=20) == 15
    assert quiz.points_for(correct=True, elapsed_seconds=10, limit=20) == 15
    assert quiz.points_for(correct=True, elapsed_seconds=19.9, limit=20) == 10
