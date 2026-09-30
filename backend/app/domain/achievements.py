"""Achievement definitions and their criteria.

Criteria are thresholds over named counters that the service layer computes from
domain facts. Keeping them here means an achievement can be unit-tested with a
dictionary, and adding one is a data change plus a test.

The design constraint from the brief: these are bragging rights. Nothing here
should be usable as a performance review, so every metric counts *contribution to
the meeting*, and none of them measures hours, output volume or availability.
"""

from __future__ import annotations

from dataclasses import dataclass

# Counter names the service layer must provide.
METRICS = frozenset(
    {
        "sessions_attended",
        "session_streak",
        "ideas_authored",
        "ideas_accepted",
        "tasks_completed",
        "tasks_completed_on_time",
        "blockers_resolved",
        "game_wins",
        "games_hosted",
        "early_bird_count",
        "comebacks",
        "seasons_top_three",
    }
)


@dataclass(frozen=True)
class AchievementSpec:
    key: str
    name: str
    description: str
    emoji: str
    metric: str
    threshold: int
    rarity: str = "common"


ACHIEVEMENTS: dict[str, AchievementSpec] = {
    spec.key: spec
    for spec in (
        AchievementSpec(
            "meeting_monster",
            "Meeting Monster",
            "Turned up to 10 sessions",
            "🐘",
            "sessions_attended",
            10,
        ),
        AchievementSpec(
            "idea_machine",
            "Idea Machine",
            "Captured 10 ideas",
            "💡",
            "ideas_authored",
            10,
        ),
        AchievementSpec(
            "project_oracle",
            "Project Oracle",
            "5 of your ideas were accepted",
            "🔮",
            "ideas_accepted",
            5,
        ),
        AchievementSpec(
            "deadline_destroyer",
            "Deadline Destroyer",
            "Finished 5 tasks on or before their due date",
            "🎯",
            "tasks_completed_on_time",
            5,
            rarity="rare",
        ),
        AchievementSpec(
            "closer",
            "Closer",
            "Completed 10 tasks",
            "✅",
            "tasks_completed",
            10,
        ),
        AchievementSpec(
            "firefighter",
            "Firefighter",
            "Put out 3 blockers",
            "🧯",
            "blockers_resolved",
            3,
            rarity="rare",
        ),
        AchievementSpec(
            "trivia_champion",
            "Trivia Champion",
            "Won 5 games",
            "🏆",
            "game_wins",
            5,
        ),
        AchievementSpec(
            "quiz_master",
            "Quiz Master",
            "Ran 5 games as host",
            "🎤",
            "games_hosted",
            5,
        ),
        AchievementSpec(
            "early_bird",
            "Early Bird",
            "First to arrive 3 times",
            "🐦",
            "early_bird_count",
            3,
        ),
        AchievementSpec(
            "comeback_king",
            "Comeback King",
            "Reopened and finished a task 3 times",
            "🔁",
            "comebacks",
            3,
        ),
        AchievementSpec(
            "mshikaki_legend",
            "Mshikaki Legend",
            "Finished top three in 2 seasons",
            "👑",
            "seasons_top_three",
            2,
            rarity="legendary",
        ),
    )
}


def earned(stats: dict[str, int]) -> list[str]:
    """Keys of every achievement the counters satisfy. Order is stable."""
    unknown = set(stats) - METRICS
    if unknown:  # pragma: no cover - guards a service bug, not user input
        raise KeyError(f"Unknown achievement metrics: {sorted(unknown)}")

    return [
        key for key, spec in ACHIEVEMENTS.items() if stats.get(spec.metric, 0) >= spec.threshold
    ]


def progress(stats: dict[str, int]) -> list[dict[str, object]]:
    """For the achievements page: what you have and how close you are."""
    rows: list[dict[str, object]] = []
    for key, spec in ACHIEVEMENTS.items():
        have = stats.get(spec.metric, 0)
        rows.append(
            {
                "key": key,
                "name": spec.name,
                "description": spec.description,
                "emoji": spec.emoji,
                "rarity": spec.rarity,
                "earned": have >= spec.threshold,
                "have": have,
                "threshold": spec.threshold,
            }
        )
    return rows
