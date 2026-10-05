"""The download is named after the meeting, not after the database."""

from __future__ import annotations

from app.domain.naming import minutes_filename, slugify


def test_a_title_becomes_a_readable_file_stem() -> None:
    assert slugify("Innovations Weekly Session #12") == "innovations-weekly-session-12"
    assert slugify("Q4 / Budget review!") == "q4-budget-review"
    assert slugify("  spaced   out  ") == "spaced-out"


def test_an_empty_or_punctuation_title_falls_back_to_the_number() -> None:
    assert minutes_filename(None, 7, "pdf") == "mshikaki-session-7-minutes.pdf"
    assert minutes_filename("", 7, "html") == "mshikaki-session-7-minutes.html"
    assert minutes_filename("!!!", 3, "txt") == "mshikaki-session-3-minutes.txt"


def test_the_extension_is_respected() -> None:
    assert minutes_filename("Board meeting", 2, "pdf") == "board-meeting-minutes.pdf"
    assert minutes_filename("Board meeting", 2, "html") == "board-meeting-minutes.html"


def test_a_very_long_title_is_trimmed() -> None:
    stem = slugify("x" * 200)
    assert len(stem) <= 60
