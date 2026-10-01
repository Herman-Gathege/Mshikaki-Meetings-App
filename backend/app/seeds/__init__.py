"""Idempotent seed data: game definitions, content packs, XP rules, achievements.

Safe to run repeatedly. Content lives in `content/packs/*.json` and is treated as
a product asset rather than as code; re-importing an edited pack replaces its
items without duplicating them.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.db.models import Achievement, ContentPack, GameDefinition, GameQuestion, XpRuleModel
from app.domain import achievements as achievement_rules
from app.domain import xp as xp_rules
from app.domain.enums import GameFamily

GAME_DEFINITIONS: list[dict] = [
    {
        "key": "prompts-rapid-fire",
        "name": "Rapid Fire",
        "family": GameFamily.PROMPT_DECK.value,
        "description": "Fast questions answered out loud. No right answer, no notes.",
        "how_to_play": "Read each card aloud. Anyone can answer. Keep it moving.",
        "typical_minutes": 5,
        "energy": "high",
        "tags": ["quick", "talkative"],
    },
    {
        "key": "prompts-icebreakers",
        "name": "Get to Know",
        "family": GameFamily.PROMPT_DECK.value,
        "description": "Questions that make a room interesting without getting personal.",
        "how_to_play": "One card at a time, everyone answers briefly, go round the room.",
        "typical_minutes": 10,
        "energy": "medium",
        "tags": ["new-people", "relaxed"],
    },
    {
        "key": "prompts-name-five",
        "name": "Name 5 Things",
        "family": GameFamily.PROMPT_DECK.value,
        "description": "Name five things in ten seconds. Harder than it sounds.",
        "how_to_play": "Read the category, count down from ten, take answers from anybody.",
        "typical_minutes": 5,
        "energy": "high",
        "tags": ["competitive", "quick"],
    },
    {
        "key": "trivia-kenya",
        "name": "Kenyan Trivia",
        "family": GameFamily.HOST_QUIZ.value,
        "description": "Counties, lakes, athletes and history.",
        "how_to_play": "Host reads, the room calls out answers, host confirms and scores.",
        "typical_minutes": 15,
        "energy": "high",
        "tags": ["kenya", "quiz"],
    },
    {
        "key": "trivia-general",
        "name": "General Trivia",
        "family": GameFamily.HOST_QUIZ.value,
        "description": "Wide, fair, and nothing that needs a specific generation.",
        "how_to_play": "Host reads, room answers, host awards points.",
        "typical_minutes": 15,
        "energy": "high",
        "tags": ["quiz", "any-audience"],
    },
    {
        "key": "true-false",
        "name": "True or False",
        "family": GameFamily.HOST_QUIZ.value,
        "description": "Thumbs up or thumbs down. Good for mixed confidence levels.",
        "how_to_play": "Read the statement, everyone votes at once, then reveal.",
        "typical_minutes": 8,
        "energy": "medium",
        "tags": ["quiz", "low-effort"],
    },
    {
        "key": "emoji-guess",
        "name": "Emoji Guess",
        "family": GameFamily.HOST_QUIZ.value,
        "description": "Guess the film, food or person from emoji alone.",
        "how_to_play": "Show the emoji, take guesses, award the point to the first correct answer.",
        "typical_minutes": 8,
        "energy": "high",
        "tags": ["visual", "laughs"],
    },
    {
        "key": "hosted-activity",
        "name": "Host-judged Activity",
        "family": GameFamily.HOST_SCORED.value,
        "description": "Acts, stories and challenges where the host decides who wins.",
        "how_to_play": "Run the activity, then enter the final standings by hand.",
        "typical_minutes": 15,
        "energy": "high",
        "tags": ["physical", "team-based"],
    },
]


def seed_game_definitions(db: DbSession) -> int:
    created = 0
    for spec in GAME_DEFINITIONS:
        existing = db.execute(
            select(GameDefinition).where(GameDefinition.key == spec["key"])
        ).scalar_one_or_none()
        if existing is not None:
            existing.name = spec["name"]
            existing.family = spec["family"]
            existing.description = spec["description"]
            existing.how_to_play = spec["how_to_play"]
            existing.typical_minutes = spec["typical_minutes"]
            existing.energy = spec["energy"]
            existing.tags = list(spec["tags"])
            continue
        db.add(GameDefinition(**spec, config_schema={}, min_players=2))
        created += 1
    db.flush()
    return created


def import_pack(db: DbSession, payload: dict) -> tuple[int, int]:
    pack = db.execute(
        select(ContentPack).where(ContentPack.key == payload["key"])
    ).scalar_one_or_none()
    if pack is None:
        pack = ContentPack(
            key=payload["key"],
            game_definition_key=payload["game_key"],
            title=payload["title"],
            description=payload.get("description"),
            language=payload.get("language", "en"),
            license=payload["license"],
            attribution=payload["attribution"],
            source_url=payload.get("source_url"),
            is_seed=True,
        )
        db.add(pack)
        created = 1
    else:
        pack.title = payload["title"]
        pack.description = payload.get("description")
        pack.game_definition_key = payload["game_key"]
        pack.license = payload["license"]
        pack.attribution = payload["attribution"]
        created = 0
    db.flush()

    items = payload.get("items", [])
    # Update in place rather than delete and re-insert. The seeder runs on every
    # container start, and a game play holds the question ids it was created with:
    # replacing the rows would empty any quiz that was in progress during a deploy.
    by_position = {question.position: question for question in pack.questions}
    for position, item in enumerate(items):
        row = by_position.pop(position, None)
        if row is None:
            db.add(
                GameQuestion(
                    content_pack_id=pack.id,
                    position=position,
                    prompt=item["prompt"],
                    answer=item.get("answer"),
                    choices=item.get("choices"),
                    category=item.get("category"),
                    difficulty=item.get("difficulty"),
                    explanation=item.get("explanation"),
                )
            )
            continue
        row.prompt = item["prompt"]
        row.answer = item.get("answer")
        row.choices = item.get("choices")
        row.category = item.get("category")
        row.difficulty = item.get("difficulty")
        row.explanation = item.get("explanation")
    # Only a pack that shrank loses rows.
    for stale in by_position.values():
        db.delete(stale)
    db.flush()
    return created, len(items)


def seed_content(db: DbSession) -> dict[str, int]:
    content_dir: Path = get_settings().content_dir
    if not content_dir.is_dir():
        return {"packs": 0, "items": 0, "missing": 1}

    packs = 0
    items = 0
    for path in sorted(content_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        created, count = import_pack(db, payload)
        packs += created
        items += count
    return {"packs": packs, "items": items, "missing": 0}


def seed_xp_rules(db: DbSession) -> int:
    created = 0
    for key, spec in xp_rules.DEFAULT_RULES.items():
        existing = db.execute(
            select(XpRuleModel).where(XpRuleModel.key == key)
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(
            XpRuleModel(
                key=key,
                label=spec.label,
                amount=spec.amount,
                max_per_session=spec.max_per_session,
                max_per_day=spec.max_per_day,
                max_per_week=spec.max_per_week,
                diminishing_after=spec.diminishing_after,
                active=True,
            )
        )
        created += 1
    db.flush()
    return created


def seed_achievements(db: DbSession) -> int:
    created = 0
    for key, spec in achievement_rules.ACHIEVEMENTS.items():
        existing = db.execute(
            select(Achievement).where(Achievement.key == key)
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(
            Achievement(
                key=spec.key,
                name=spec.name,
                description=spec.description,
                emoji=spec.emoji,
                rarity=spec.rarity,
                criteria={"metric": spec.metric, "threshold": spec.threshold},
            )
        )
        created += 1
    db.flush()
    return created


def seed_all(db: DbSession) -> dict[str, object]:
    games_created = seed_game_definitions(db)
    content = seed_content(db)
    rules_created = seed_xp_rules(db)
    achievements_created = seed_achievements(db)
    db.commit()
    return {
        "game_definitions_created": games_created,
        "content_packs_created": content["packs"],
        "content_items": content["items"],
        "content_dir_missing": content["missing"],
        "xp_rules_created": rules_created,
        "achievements_created": achievements_created,
    }
