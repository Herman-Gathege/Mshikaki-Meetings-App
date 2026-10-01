"""Game library, play and scoring.

A quiz question is live for the whole room at once. Every phone shows the same
countdown because the clock lives on the play (`question_started_at`), not in a
browser, and a player who answers is locked in without stopping anybody else's
timer. When the host reveals the answer the right answers are scored in one go:
ten points, plus five for answering in the first half of the clock.

The host is always right: every automatic score can be corrected afterwards, and
the correction is recorded with a reason. Games without a right answer (prompt
decks) keep the manual "+10" the host presses while the room talks.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.db.models import (
    ContentPack,
    GameAnswer,
    GameDefinition,
    GamePlay,
    GameQuestion,
    GameScore,
    Guest,
    SessionParticipant,
    User,
)
from app.db.models import Session as MeetingSession
from app.domain import quiz as quiz_rules
from app.domain.enums import GameFamily, GamePlayStatus, ParticipantRole
from app.errors import AppError, NotFoundError
from app.services.activity import record_activity


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _question_seconds(settings: dict | None) -> int:
    """How long a question stays open. Configurable, with a sane default."""
    raw = (settings or {}).get("question_seconds", quiz_rules.DEFAULT_QUESTION_SECONDS)
    try:
        seconds = int(raw)
    except (TypeError, ValueError):
        return quiz_rules.DEFAULT_QUESTION_SECONDS
    return min(max(seconds, 5), 300)


def list_definitions(db: DbSession) -> list[dict]:
    rows = db.execute(
        select(GameDefinition).where(GameDefinition.active.is_(True)).order_by(GameDefinition.name)
    ).scalars()
    return [
        {
            "key": row.key,
            "name": row.name,
            "family": row.family,
            "description": row.description,
            "how_to_play": row.how_to_play,
            "min_players": row.min_players,
            "max_players": row.max_players,
            "typical_minutes": row.typical_minutes,
            "energy": row.energy,
            "tags": row.tags,
        }
        for row in rows
    ]


def list_packs(db: DbSession, *, family: str | None = None) -> list[dict]:
    query = select(ContentPack).where(ContentPack.deleted_at.is_(None))
    if family:
        keys = [
            row.key
            for row in db.execute(
                select(GameDefinition).where(GameDefinition.family == family)
            ).scalars()
        ]
        query = query.where(ContentPack.game_definition_key.in_(keys))
    packs = list(db.execute(query.order_by(ContentPack.title)).scalars())

    counts: dict[uuid.UUID, int] = {}
    for row in db.execute(select(GameQuestion.content_pack_id, GameQuestion.id)).all():
        counts[row[0]] = counts.get(row[0], 0) + 1

    return [
        {
            "id": str(pack.id),
            "key": pack.key,
            "title": pack.title,
            "description": pack.description,
            "game_key": pack.game_definition_key,
            "items": counts.get(pack.id, 0),
            "license": pack.license,
            "attribution": pack.attribution,
        }
        for pack in packs
    ]


def create_play(
    db: DbSession,
    *,
    session: MeetingSession,
    actor,
    actor_name: str,
    game_key: str,
    pack_id: uuid.UUID | None,
    settings: dict | None = None,
) -> GamePlay:
    definition = db.execute(
        select(GameDefinition).where(GameDefinition.key == game_key)
    ).scalar_one_or_none()
    if definition is None:
        raise NotFoundError("That game does not exist.")

    question_order: list[str] = []
    if pack_id is not None:
        pack = db.get(ContentPack, pack_id)
        if pack is None:
            raise NotFoundError("That content pack does not exist.")
        ids = [
            str(row)
            for row in db.execute(
                select(GameQuestion.id)
                .where(GameQuestion.content_pack_id == pack_id)
                .order_by(GameQuestion.position)
            ).scalars()
        ]
        question_order = ids

    play = GamePlay(
        session_id=session.id,
        game_definition_key=definition.key,
        content_pack_id=pack_id,
        host_id=actor.user_id,
        status=GamePlayStatus.RUNNING.value,
        settings=settings or {},
        question_order=question_order,
        current_index=0,
        started_at=_now(),
        question_seconds=_question_seconds(settings),
        # The first question is live the moment the game is. Nobody waits for the
        # host to press a second button.
        question_started_at=_now() if question_order else None,
    )
    db.add(play)
    db.flush()

    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="game.started",
        target_type="game_play",
        target_id=play.id,
        payload={"game": definition.name},
    )
    return play


def get_play(db: DbSession, *, team_id: uuid.UUID, play_id: uuid.UUID) -> GamePlay:
    play = db.get(GamePlay, play_id)
    if play is None:
        raise NotFoundError("That game play does not exist.")
    session = db.get(MeetingSession, play.session_id)
    if session is None or session.team_id != team_id:
        raise NotFoundError("That game play does not exist.")
    return play


def current_question(db: DbSession, play: GamePlay) -> GameQuestion | None:
    order = play.question_order or []
    if play.current_index >= len(order):
        return None
    return db.get(GameQuestion, uuid.UUID(order[play.current_index]))


def _player_count(db: DbSession, session_id: uuid.UUID) -> int:
    """How many people in the room could answer: present, not observing."""
    return int(
        db.execute(
            select(func.count())
            .select_from(SessionParticipant)
            .where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.role != ParticipantRole.OBSERVER.value,
            )
        ).scalar_one()
    )


def _may_see_the_answer(db: DbSession, play: GamePlay, actor) -> bool:
    """The host and the staff see the answer before the reveal; the room does not."""
    if actor is None:
        return False
    if getattr(actor, "is_staff", False):
        return True
    if actor.user_id is None:
        return False
    if play.host_id is not None and actor.user_id == play.host_id:
        return True
    session = db.get(MeetingSession, play.session_id)
    return bool(session is not None and session.facilitator_id == actor.user_id)


def play_state(db: DbSession, play: GamePlay, *, actor=None) -> dict:
    definition = db.execute(
        select(GameDefinition).where(GameDefinition.key == play.game_definition_key)
    ).scalar_one_or_none()
    pack = db.get(ContentPack, play.content_pack_id) if play.content_pack_id else None
    question = current_question(db, play)
    total = len(play.question_order or [])
    now = _now()
    revealed = play.revealed_at is not None
    sees_the_answer = revealed or _may_see_the_answer(db, play, actor)
    limit = play.question_seconds or quiz_rules.DEFAULT_QUESTION_SECONDS

    answers = (
        list(
            db.execute(
                select(GameAnswer).where(
                    GameAnswer.game_play_id == play.id,
                    GameAnswer.question_id == question.id,
                )
            ).scalars()
        )
        if question is not None
        else []
    )
    mine = None
    if actor is not None:
        mine = next(
            (
                row
                for row in answers
                if (actor.user_id is not None and row.user_id == actor.user_id)
                or (actor.guest_id is not None and row.guest_id == actor.guest_id)
            ),
            None,
        )

    return {
        "id": str(play.id),
        "session_id": str(play.session_id),
        "host_id": str(play.host_id) if play.host_id else None,
        "game": {
            "key": play.game_definition_key,
            "name": definition.name if definition else play.game_definition_key,
            "family": definition.family if definition else GameFamily.PROMPT_DECK.value,
            "how_to_play": definition.how_to_play if definition else None,
        },
        "pack": {"id": str(pack.id), "title": pack.title} if pack else None,
        "status": play.status,
        "index": play.current_index,
        "total": total,
        "answered": {"count": len(answers), "of": _player_count(db, play.session_id)},
        "question": (
            {
                "id": str(question.id),
                "prompt": question.prompt,
                "choices": question.choices,
                "category": question.category,
                "media_url": question.media_url,
                "answer": question.answer if sees_the_answer else None,
                "explanation": question.explanation if sees_the_answer else None,
                "seconds": limit,
                # The clock is the server's. A phone only draws it.
                "seconds_left": quiz_rules.seconds_left(play.question_started_at, limit, now),
                "started_at": play.question_started_at.isoformat()
                if play.question_started_at
                else None,
                "revealed": revealed,
                "open": quiz_rules.is_accepting_answers(
                    started_at=play.question_started_at,
                    limit=limit,
                    revealed_at=play.revealed_at,
                    now=now,
                ),
            }
            if question
            else None
        ),
        "you": {
            "answer": mine.choice if mine else None,
            "correct": mine.correct if mine else None,
            "answered": mine is not None,
        },
        "scores": [
            {
                "id": str(score.id),
                "user_id": str(score.user_id) if score.user_id else None,
                "guest_id": str(score.guest_id) if score.guest_id else None,
                "player_name": score.player_name,
                "points": score.points,
                "correct_count": score.correct_count,
                "position": score.position,
            }
            for score in sorted(play.scores, key=lambda s: s.points, reverse=True)
        ],
    }


def next_question(db: DbSession, *, play: GamePlay, actor, actor_name: str) -> GamePlay:
    total = len(play.question_order or [])
    if total and play.current_index + 1 < total:
        play.current_index += 1
        db.flush()
        _open_question(play)
    return play


def previous_question(db: DbSession, *, play: GamePlay, actor, actor_name: str) -> GamePlay:
    if play.current_index > 0:
        play.current_index -= 1
        db.flush()
        _open_question(play)
    return play


def _open_question(play: GamePlay) -> None:
    """Put the current question live for the room and close the last one.

    Called whenever the question changes, so every phone starts the same clock
    again and the previous answer is no longer on screen.
    """
    play.question_started_at = _now()
    play.revealed_at = None


def _player_name(db: DbSession, *, user_id: uuid.UUID | None, guest_id: uuid.UUID | None) -> str:
    if user_id is not None:
        user = db.get(User, user_id)
        return user.display_name if user else "Someone"
    guest = db.get(Guest, guest_id) if guest_id is not None else None
    return guest.display_name if guest else "A guest"


def submit_answer(
    db: DbSession,
    *,
    play: GamePlay,
    actor,
    choice: str,
) -> GameAnswer:
    """Lock in one player's answer. Answering again is a no-op, not an error."""
    if play.status != GamePlayStatus.RUNNING.value:
        raise AppError("This game has already finished.", code="game.not_running")

    if actor.user_id is None and actor.guest_id is None:
        raise AppError("Sign in to play.", code="game.no_player")

    question = current_question(db, play)
    if question is None:
        raise AppError("There is no question to answer yet.", code="game.no_question")

    picked = choice.strip()
    offered = [str(option) for option in (question.choices or [])]
    if offered and picked not in offered:
        raise AppError("That is not one of the options.", code="game.bad_choice")
    if not picked:
        raise AppError("Pick an answer first.", code="game.no_choice")

    subject = (
        GameAnswer.user_id == actor.user_id
        if actor.user_id is not None
        else GameAnswer.guest_id == actor.guest_id
    )
    existing = db.execute(
        select(GameAnswer).where(
            GameAnswer.game_play_id == play.id,
            GameAnswer.question_id == question.id,
            subject,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    limit = play.question_seconds or quiz_rules.DEFAULT_QUESTION_SECONDS
    if not quiz_rules.is_accepting_answers(
        started_at=play.question_started_at,
        limit=limit,
        revealed_at=play.revealed_at,
        now=_now(),
    ):
        raise AppError("Time is up for this question.", code="game.too_late")

    answer = GameAnswer(
        game_play_id=play.id,
        question_id=question.id,
        user_id=actor.user_id,
        guest_id=actor.guest_id,
        player_name=_player_name(db, user_id=actor.user_id, guest_id=actor.guest_id),
        choice=picked,
        submitted_at=_now(),
    )
    db.add(answer)
    db.flush()
    return answer


def reveal_question(
    db: DbSession, *, play: GamePlay, session: MeetingSession, actor, actor_name: str
) -> GamePlay:
    """Close the window and score the right answers, once."""
    if play.revealed_at is not None:
        return play

    question = current_question(db, play)
    if question is None:
        raise AppError("There is nothing to reveal.", code="game.no_question")

    play.revealed_at = _now()
    db.flush()

    scored: list[dict] = []
    if question.answer:
        for answer in db.execute(
            select(GameAnswer).where(
                GameAnswer.game_play_id == play.id, GameAnswer.question_id == question.id
            )
        ).scalars():
            correct = quiz_rules.answer_is_correct(answer.choice, question.answer)
            answer.correct = correct
            # Every player who answered gets a row, right or wrong: the row is
            # what "played a game" is paid from at the end, and somebody who
            # answered badly still showed up.
            row = _score_row(
                db,
                play=play,
                user_id=answer.user_id,
                guest_id=answer.guest_id,
                player_name=answer.player_name,
            )
            if not correct:
                continue
            elapsed = (
                (answer.submitted_at - play.question_started_at).total_seconds()
                if play.question_started_at
                else 0.0
            )
            points = quiz_rules.points_for(
                correct=True,
                elapsed_seconds=elapsed,
                limit=play.question_seconds or quiz_rules.DEFAULT_QUESTION_SECONDS,
            )
            row.points += points
            row.correct_count += 1
            row.source = "auto"
            answer.points_awarded = points
            scored.append({"name": answer.player_name, "points": points})
        db.flush()

    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="game.answer_revealed",
        target_type="game_play",
        target_id=play.id,
        payload={
            "game": play.game_definition_key,
            "question": question.prompt[:120],
            "answer": question.answer,
            "scored": scored,
        },
    )
    return play


def _score_row(
    db: DbSession,
    *,
    play: GamePlay,
    user_id: uuid.UUID | None,
    guest_id: uuid.UUID | None,
    player_name: str,
) -> GameScore:
    query = select(GameScore).where(GameScore.game_play_id == play.id)
    if user_id is not None:
        query = query.where(GameScore.user_id == user_id)
    else:
        query = query.where(GameScore.guest_id == guest_id)
    row = db.execute(query).scalar_one_or_none()
    if row is None:
        row = GameScore(
            game_play_id=play.id,
            user_id=user_id,
            guest_id=guest_id,
            player_name=player_name,
            points=0,
            correct_count=0,
            source="host",
        )
        db.add(row)
        db.flush()
    return row


def award_points(
    db: DbSession,
    *,
    play: GamePlay,
    session: MeetingSession,
    actor,
    actor_name: str,
    user_id: uuid.UUID | None = None,
    guest_id: uuid.UUID | None = None,
    points: int = 10,
    correct: bool = True,
    reason: str | None = None,
    override: bool = False,
) -> GameScore:
    if user_id is None and guest_id is None:
        raise AppError("Pick a player first.", code="score.no_player")
    if points == 0:
        raise AppError("Award at least one point.", code="score.no_points")

    player_name = "Someone"
    if user_id is not None:
        user = db.get(User, user_id)
        player_name = user.display_name if user else "Someone"
    elif guest_id is not None:
        guest = db.get(Guest, guest_id)
        player_name = guest.display_name if guest else "A guest"

    row = _score_row(db, play=play, user_id=user_id, guest_id=guest_id, player_name=player_name)
    previous = row.points

    if override:
        row.points = points
        row.adjusted_by = actor.user_id if actor else None
        row.adjustment_reason = reason or "host correction"
        row.source = "host"
    else:
        row.points += points
        if correct:
            row.correct_count += 1
    db.flush()

    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="game.score_adjusted" if override else "game.point_awarded",
        target_type="game_play",
        target_id=play.id,
        payload={
            "game": play.game_definition_key,
            "player": player_name,
            "old": previous,
            "new": row.points,
            "points": abs(row.points - previous) or points,
            "reason": reason or ("host correction" if override else "awarded"),
            "winner": player_name,
        },
    )
    return row


def finish_play(
    db: DbSession, *, play: GamePlay, session: MeetingSession, actor, actor_name: str
) -> GamePlay:
    if play.status == GamePlayStatus.FINISHED.value:
        return play

    ordered = sorted(play.scores, key=lambda score: score.points, reverse=True)
    for index, score in enumerate(ordered, start=1):
        score.position = index
    play.status = GamePlayStatus.FINISHED.value
    play.ended_at = datetime.now(timezone.utc)
    db.flush()

    definition = db.execute(
        select(GameDefinition).where(GameDefinition.key == play.game_definition_key)
    ).scalar_one_or_none()
    winner = ordered[0].player_name if ordered else None

    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="game.finished",
        target_type="game_play",
        target_id=play.id,
        payload={
            "game": definition.name if definition else play.game_definition_key,
            "winner": winner or "nobody",
        },
    )

    _award_placements(
        db, play=play, session=session, ordered=ordered, actor=actor, actor_name=actor_name
    )
    return play


def _award_placements(
    db: DbSession,
    *,
    play: GamePlay,
    session: MeetingSession,
    ordered: list[GameScore],
    actor,
    actor_name: str,
) -> None:
    from app.services.bragging import award_for_event

    for score in ordered:
        if score.user_id is None:
            continue
        rule_key = (
            "game_won"
            if score.position == 1
            else "game_placed"
            if score.position in (2, 3)
            else None
        )
        award_for_event(
            db,
            team_id=session.team_id,
            user_id=score.user_id,
            subject_name=score.player_name,
            rule_key="game_played",
            source_type="game_play",
            source_id=play.id,
            session_id=session.id,
            actor=actor,
            actor_name=actor_name,
        )
        if rule_key is not None:
            award_for_event(
                db,
                team_id=session.team_id,
                user_id=score.user_id,
                subject_name=score.player_name,
                rule_key=rule_key,
                source_type="game_play",
                source_id=play.id,
                session_id=session.id,
                actor=actor,
                actor_name=actor_name,
            )


def abandon_play(
    db: DbSession, *, play: GamePlay, session: MeetingSession, actor, actor_name: str
) -> GamePlay:
    play.status = GamePlayStatus.ABANDONED.value
    play.ended_at = datetime.now(timezone.utc)
    db.flush()
    record_activity(
        db,
        team_id=session.team_id,
        session_id=session.id,
        actor=actor,
        actor_name=actor_name,
        verb="game.abandoned",
        target_type="game_play",
        target_id=play.id,
        payload={"game": play.game_definition_key},
    )
    return play


def session_players(db: DbSession, session: MeetingSession) -> list[dict]:
    """Who the host can award points to: present participants, in name order."""
    players: list[dict] = []
    for participant in session.participants:
        if participant.role == ParticipantRole.OBSERVER.value:
            continue
        name = "Someone"
        if participant.user_id is not None:
            user = db.get(User, participant.user_id)
            name = user.display_name if user else "Someone"
        elif participant.guest_id is not None:
            guest = db.get(Guest, participant.guest_id)
            name = guest.display_name if guest else "A guest"
        players.append(
            {
                "user_id": str(participant.user_id) if participant.user_id else None,
                "guest_id": str(participant.guest_id) if participant.guest_id else None,
                "name": name,
                "attended": participant.attended,
            }
        )
    return sorted(players, key=lambda row: row["name"])


def shuffle_questions(db: DbSession, *, play: GamePlay, actor, actor_name: str) -> GamePlay:
    order = list(play.question_order or [])
    random.shuffle(order)
    play.question_order = order
    play.current_index = 0
    db.flush()
    return play
