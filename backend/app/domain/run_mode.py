"""Run Mode: one facilitator drives, everybody follows.

Pure rules for the shared meeting state, so the stage list and the release
behaviour are testable without a database.
"""

from __future__ import annotations

from app.domain.enums import SessionStatus

STAGES: tuple[str, ...] = ("play", "agenda", "capture", "decide", "assign", "close")

# The journey a meeting actually takes. `capture`, `decide` and `assign` are the
# older per-topic screens: they stay valid so a meeting sitting on one of them is
# never stranded, but the agenda carries the room now, and the agenda screen holds
# the work those three used to split up.
MAIN_PATH: tuple[str, ...] = ("play", "agenda", "close")

DEFAULT_STAGE = "play"


class UnknownStage(Exception):
    def __init__(self, stage: str) -> None:
        super().__init__(f"'{stage}' is not a Run Mode stage")
        self.stage = stage


def is_stage(stage: str) -> bool:
    return stage in STAGES


def ensure_stage(stage: str) -> str:
    if not is_stage(stage):
        raise UnknownStage(stage)
    return stage


def next_stage(stage: str) -> str | None:
    """The stage after this one, or None at the end of the meeting."""
    index = STAGES.index(ensure_stage(stage))
    return STAGES[index + 1] if index + 1 < len(STAGES) else None


def is_running(status: str, stage: str | None) -> bool:
    """Is the room currently inside Run Mode?"""
    return status in {SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value} and stage is not None


def stage_for_release() -> None:
    """Closing a meeting clears the stage: everybody gets their navigation back."""
    return None
