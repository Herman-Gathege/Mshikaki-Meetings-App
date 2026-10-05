"""Names for the things a meeting produces.

The downloaded minutes used to be `minutes-12.pdf`, which tells a person
nothing six months later. They are named after the meeting instead, because the
title is the only part somebody types themselves.
"""

from __future__ import annotations

MAX_STEM = 60


def slugify(title: str | None) -> str:
    """A safe, readable file stem. Keeps letters and numbers, hyphenates the rest."""
    if not title:
        return ""
    kept = [character.lower() if character.isalnum() else "-" for character in title.strip()]
    collapsed = "".join(kept)
    while "--" in collapsed:
        collapsed = collapsed.replace("--", "-")
    return collapsed.strip("-")[:MAX_STEM].strip("-")


def minutes_filename(title: str | None, sequence_no: int, extension: str) -> str:
    """`Innovations Weekly #12` becomes `innovations-weekly-12-minutes.pdf`.

    A title that is empty, or made only of punctuation, falls back to the
    meeting number so a download never lands as `-minutes.pdf`.
    """
    stem = slugify(title)
    if not stem:
        return f"mshikaki-session-{sequence_no}-minutes.{extension}"
    return f"{stem}-minutes.{extension}"
