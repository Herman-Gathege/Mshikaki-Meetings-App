"""Naming people with @ in a note."""

from __future__ import annotations

from app.domain.mentions import find_mentions

ROOM = [
    {"id": "1", "name": "Anne"},
    {"id": "2", "name": "Anne Wanjiku"},
    {"id": "3", "name": "Brian"},
]


def test_a_name_is_found() -> None:
    assert find_mentions("@Brian chase the invoice", ROOM) == [{"id": "3", "name": "Brian"}]


def test_the_longest_name_wins() -> None:
    """'Anne Wanjiku' must not be read as 'Anne'."""
    found = find_mentions("@Anne Wanjiku please confirm", ROOM)
    assert found == [{"id": "2", "name": "Anne Wanjiku"}]


def test_two_people_are_both_named() -> None:
    found = find_mentions("@Anne and @Brian, this one is yours", ROOM)
    assert [row["name"] for row in found] == ["Anne", "Brian"]


def test_naming_somebody_twice_returns_them_once() -> None:
    found = find_mentions("@Brian and again @Brian", ROOM)
    assert len(found) == 1


def test_an_at_that_names_nobody_is_left_alone() -> None:
    assert find_mentions("@Nobody is here", ROOM) == []
    assert find_mentions("no names here", ROOM) == []
    assert find_mentions("", ROOM) == []
