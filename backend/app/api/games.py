"""The game library and the host console."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can, require_capability
from app.domain.permissions import Resource
from app.schemas import AnswerRequest, PlayCreateRequest, ScoreAwardRequest, ScoreOverrideRequest
from app.services import games, meetings, questions

router = APIRouter(tags=["games"])


def play_resource(context, session) -> Resource:
    return Resource(
        team_id=context.team.id,
        session_id=session.id,
        session_facilitator_id=session.facilitator_id,
        session_status=session.status,
    )


@router.get("/games")
def list_games(db: DbSession = DbDep, context=ContextDep) -> dict:  # type: ignore[assignment]
    return {"items": games.list_definitions(db)}


@router.get("/games/packs")
def list_packs(
    family: str | None = None,
    db: DbSession = DbDep,
    context=ContextDep,  # type: ignore[assignment]
) -> dict:
    return {"items": games.list_packs(db, family=family)}


@router.post("/sessions/{session_id}/games")
def start_play(
    session_id: uuid.UUID,
    payload: PlayCreateRequest,
    context=require_capability("game.launch"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    pack_id = payload.content_pack_id
    if payload.use_session_questions:
        # The room's own questions become the pack this game plays.
        pack = questions.pack_for_session(
            db, session=session, actor=context.actor, actor_name=context.name
        )
        pack_id = pack.id
    play = games.create_play(
        db,
        session=session,
        actor=context.actor,
        actor_name=context.name,
        game_key=payload.game_key,
        pack_id=pack_id,
        settings=payload.settings,
    )
    return games.play_state(db, play, actor=context.actor)


@router.get("/sessions/{session_id}/players")
def session_players(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    return {"items": games.session_players(db, session)}


@router.get("/game-plays/{play_id}")
def get_play(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/answer")
def answer_question(
    play_id: uuid.UUID,
    payload: AnswerRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    """A player's own answer. Locking in never stops anybody else's clock."""
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.answer", play_resource(context, session))
    games.submit_answer(db, play=play, actor=context.actor, choice=payload.choice)
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/reveal")
def reveal_answer(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    """Close the question and score whoever got it right."""
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.reveal_question(
        db, play=play, session=session, actor=context.actor, actor_name=context.name
    )
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/next")
def next_question(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.next_question(db, play=play, actor=context.actor, actor_name=context.name)
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/previous")
def previous_question(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.previous_question(db, play=play, actor=context.actor, actor_name=context.name)
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/shuffle")
def shuffle_questions(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.shuffle_questions(db, play=play, actor=context.actor, actor_name=context.name)
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/score")
def award_points(
    play_id: uuid.UUID,
    payload: ScoreAwardRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.award_points(
        db,
        play=play,
        session=session,
        actor=context.actor,
        actor_name=context.name,
        user_id=payload.user_id,
        guest_id=payload.guest_id,
        points=payload.points,
        correct=payload.correct,
    )
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/override")
def override_score(
    play_id: uuid.UUID,
    payload: ScoreOverrideRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score.override", play_resource(context, session))
    games.award_points(
        db,
        play=play,
        session=session,
        actor=context.actor,
        actor_name=context.name,
        user_id=payload.user_id,
        guest_id=payload.guest_id,
        points=payload.points,
        reason=payload.reason,
        override=True,
    )
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/finish")
def finish_play(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.finish_play(db, play=play, session=session, actor=context.actor, actor_name=context.name)
    return games.play_state(db, play, actor=context.actor)


@router.post("/game-plays/{play_id}/abandon")
def abandon_play(
    play_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    play = games.get_play(db, team_id=context.team.id, play_id=play_id)
    session = meetings.get_session(db, team_id=context.team.id, session_id=play.session_id)
    ensure_can(context.actor, "game.score", play_resource(context, session))
    games.abandon_play(db, play=play, session=session, actor=context.actor, actor_name=context.name)
    return games.play_state(db, play, actor=context.actor)
