"""A deploy must not break a game that is already running.

The container seeds its content on every start. If seeding replaced question
rows, a quiz in progress would lose its questions mid-meeting, which is exactly
the kind of failure that ruins a session.
"""

from __future__ import annotations

import pytest
from app.db.session import get_session_factory
from app.seeds import seed_all
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_reseeding_keeps_an_in_flight_game_playable(
    client: AsyncClient, unique_suffix: str
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"seed.{unique_suffix}@kbc.co.ke",
            "display_name": "Seeder Test",
            "password": "a-good-password",
            "team_name": f"Seed {unique_suffix}",
        },
    )
    session_id = (await client.post("/api/sessions", json={"title": "Seeded"})).json()["id"]
    await client.post(f"/api/sessions/{session_id}/start")

    packs = (await client.get("/api/games/packs", params={"family": "host_quiz"})).json()["items"]
    kenya = next(pack for pack in packs if pack["game_key"] == "trivia-kenya")
    play = (
        await client.post(
            f"/api/sessions/{session_id}/games",
            json={"game_key": "trivia-kenya", "content_pack_id": kenya["id"]},
        )
    ).json()
    original_question = play["question"]["prompt"]
    assert original_question

    # This is what the container entrypoint does on every start.
    with get_session_factory()() as db:
        seed_all(db)

    after = (await client.get(f"/api/game-plays/{play['id']}")).json()
    assert after["question"] is not None, "the running game lost its questions"
    assert after["question"]["prompt"] == original_question
    assert after["question"]["choices"]
