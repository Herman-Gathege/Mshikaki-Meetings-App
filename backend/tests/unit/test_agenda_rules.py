"""Agenda arithmetic and vocabulary, without a database."""

from __future__ import annotations

import pytest
from app.domain import agenda


def test_progress_counts_the_way_a_facilitator_speaks() -> None:
    assert (agenda.progress(0, 4).position, agenda.progress(0, 4).remaining) == (1, 3)
    assert (agenda.progress(2, 4).position, agenda.progress(2, 4).remaining) == (3, 1)
    assert agenda.progress(3, 4).is_last is True
    assert agenda.progress(2, 4).is_last is False


def test_no_current_item_is_not_the_first_item() -> None:
    """After the last item the room is at the wrap, not back at number one."""
    finished = agenda.progress(-1, 4)
    assert finished.position == 0
    assert finished.remaining == 4
    assert agenda.progress(0, 0) == agenda.Progress(position=0, total=0, remaining=0)


def test_the_agenda_finishes_and_stops() -> None:
    assert agenda.next_index(0, 3) == 1
    assert agenda.next_index(2, 3) is None
    assert agenda.next_index(0, 0) is None


@pytest.mark.parametrize("outcome", ["accomplished", "pending", "assigned", "none"])
def test_the_four_outcomes_are_known(outcome: str) -> None:
    assert agenda.ensure_outcome(outcome) == outcome
    assert agenda.OUTCOME_LABELS[outcome]


def test_an_unknown_outcome_is_refused() -> None:
    with pytest.raises(agenda.UnknownOutcome):
        agenda.ensure_outcome("pendingish")
