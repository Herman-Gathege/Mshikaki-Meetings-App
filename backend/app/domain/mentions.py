"""Naming somebody with @ in a note.

Typing the people in the room is how a note becomes somebody's job: "@Anne
chase the invoice" should not need a second control to say who it is for. The
matching is deliberately plain: the longest name wins, so "Anne Wanjiku" is not
read as "Anne", and an @ that matches nobody is left as typed rather than
guessed at.
"""

from __future__ import annotations

MENTION = "@"


def find_mentions(body: str, people: list[dict]) -> list[dict]:
    """People named in the text, in the order they are named.

    Each person is `{"id": str, "name": str}`. The longest matching name wins,
    and each person is returned once.

    A name that has been matched is consumed before shorter names are tried, so
    "@Anne Wanjiku" is not also read as "@Anne".
    """
    if not body or MENTION not in body:
        return []

    remaining = body.lower()
    found: list[tuple[int, dict]] = []
    seen: set[str] = set()
    for person in sorted(people, key=lambda row: len(str(row.get("name") or "")), reverse=True):
        name = str(person.get("name") or "").strip()
        identifier = str(person.get("id") or "")
        if not name or not identifier or identifier in seen:
            continue
        token = f"{MENTION}{name}".lower()
        position = remaining.find(token)
        if position >= 0:
            found.append((position, {"id": identifier, "name": name}))
            seen.add(identifier)
            # Same length, so positions found later still line up with the text.
            remaining = remaining.replace(token, " ")
    # Named in the order they appear, which is also who the note belongs to.
    return [person for _, person in sorted(found, key=lambda pair: pair[0])]
