"""Two people, one question, one clock.

The room noticed that answering stopped their own timer, and that a joiner was
shown the host choosing a game after the game had started. These tests hold the
fixed behaviour: the question is live for everybody at the same time, a player
answers once, and answering never closes the window for anybody else.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, *, email: str, name: str, team: str, code: str = ""):
    body: dict[str, str] = {
        "email": email,
        "display_name": name,
        "password": "a-good-password",
    }
    if code:
        body["invite_code"] = code
    else:
        body["team_name"] = team
    response = await client.post("/api/auth/register", json=body)
    assert response.status_code == 200, response.text
    return response.json()


async def _quiz_play(client: AsyncClient, session_id: str) -> dict:
    packs = (await client.get("/api/games/packs", params={"family": "host_quiz"})).json()["items"]
    pack = next(pack for pack in packs if pack["game_key"] == "trivia-kenya")
    started = await client.post(
        f"/api/sessions/{session_id}/games",
        json={"game_key": "trivia-kenya", "content_pack_id": pack["id"]},
    )
    assert started.status_code == 200, started.text
    return started.json()


async def test_the_room_plays_the_same_live_question(
    client: AsyncClient, unique_suffix: str
) -> None:
    await _register(
        client,
        email=f"host.{unique_suffix}@kbc.co.ke",
        name="Host",
        team=f"Live {unique_suffix}",
    )
    session = (
        await client.post("/api/sessions", json={"title": f"Live quiz {unique_suffix}"})
    ).json()
    assert (await client.post(f"/api/sessions/{session['id']}/start")).status_code == 200

    invite = (await client.post("/api/team/invites", json={"role": "member"})).json()
    player = AsyncClient(
        transport=client._transport,  # type: ignore[attr-defined]
        base_url="http://test",
        headers=dict(client.headers),
    )
    async with player:
        identity = await _register(
            player,
            email=f"player.{unique_suffix}@kbc.co.ke",
            name="Player",
            team="",
            code=invite["code"],
        )
        added = await client.post(
            f"/api/sessions/{session['id']}/participants",
            json={"user_id": identity["user"]["id"], "role": "participant"},
        )
        assert added.status_code == 200, added.text

        play = await _quiz_play(client, session["id"])
        play_id = play["id"]
        correct_option = play["question"]["answer"]
        assert correct_option, "the host needs the answer"

        # The player follows the same question the host started, on their own phone.
        seen = (await player.get(f"/api/game-plays/{play_id}")).json()
        assert seen["question"]["prompt"] == play["question"]["prompt"]
        assert seen["question"]["choices"] == play["question"]["choices"]
        assert seen["question"]["answer"] is None, "the room must not be handed the answer"
        assert seen["question"]["open"] is True
        assert 0 < seen["question"]["seconds_left"] <= seen["question"]["seconds"]
        assert seen["you"] == {"answer": None, "correct": None, "answered": False}
        assert seen["answered"] == {"count": 0, "of": 2}

        # They lock in. Somebody else's clock keeps running.
        answered = await player.post(
            f"/api/game-plays/{play_id}/answer", json={"choice": correct_option}
        )
        assert answered.status_code == 200, answered.text
        state = answered.json()
        assert state["you"] == {"answer": correct_option, "correct": None, "answered": True}
        assert state["answered"] == {"count": 1, "of": 2}
        assert state["question"]["open"] is True, "one answer must not close the question"
        assert state["question"]["seconds_left"] > 0

        # Pressing twice is the same answer, not an error and not a second point.
        again = await player.post(
            f"/api/game-plays/{play_id}/answer", json={"choice": correct_option}
        )
        assert again.status_code == 200
        assert again.json()["answered"] == {"count": 1, "of": 2}

        # The host can see somebody is in, and knows how many are still deciding.
        host_view = (await client.get(f"/api/game-plays/{play_id}")).json()
        assert host_view["answered"] == {"count": 1, "of": 2}

        # Reveal: the room is told the answer and the quick right answer scores.
        revealed = await client.post(f"/api/game-plays/{play_id}/reveal")
        assert revealed.status_code == 200, revealed.text
        assert revealed.json()["question"]["revealed"] is True
        assert revealed.json()["question"]["open"] is False
        scores = {(row["user_id"] or row["guest_id"]): row for row in revealed.json()["scores"]}
        assert scores[identity["user"]["id"]]["points"] == 15
        assert scores[identity["user"]["id"]]["correct_count"] == 1

        after = (await player.get(f"/api/game-plays/{play_id}")).json()
        assert after["question"]["answer"] == correct_option
        assert after["you"]["correct"] is True

        # Revealing twice changes nothing.
        twice = await client.post(f"/api/game-plays/{play_id}/reveal")
        assert twice.status_code == 200
        assert twice.json()["scores"][0]["points"] == 15

        # The next question opens a fresh window for everybody.
        nxt = (await client.post(f"/api/game-plays/{play_id}/next")).json()
        assert nxt["question"]["open"] is True
        assert nxt["question"]["revealed"] is False
        assert nxt["you"]["answer"] is None
        assert nxt["answered"] == {"count": 0, "of": 2}

        # A wrong answer still counts as playing, and scores nothing.
        wrong = next(
            option for option in nxt["question"]["choices"] if option != nxt["question"]["answer"]
        )
        await player.post(f"/api/game-plays/{play_id}/answer", json={"choice": wrong})
        closed = (await client.post(f"/api/game-plays/{play_id}/reveal")).json()
        scores = {(row["user_id"] or row["guest_id"]): row for row in closed["scores"]}
        assert scores[identity["user"]["id"]]["points"] == 15
        assert scores[identity["user"]["id"]]["correct_count"] == 1

        # And the reveal is on the record.
        trail = (await client.get("/api/activity", params={"session_id": session["id"]})).json()
        verbs = [item["verb"] for item in trail["items"]]
        assert "game.answer_revealed" in verbs


async def test_answering_is_refused_when_the_question_is_closed(
    client: AsyncClient, unique_suffix: str
) -> None:
    await _register(
        client,
        email=f"closed.{unique_suffix}@kbc.co.ke",
        name="Closed",
        team=f"Closed {unique_suffix}",
    )
    session = (await client.post("/api/sessions", json={"title": "Closed"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")
    play = await _quiz_play(client, session["id"])

    await client.post(f"/api/game-plays/{play['id']}/reveal")
    refused = await client.post(
        f"/api/game-plays/{play['id']}/answer",
        json={"choice": play["question"]["choices"][0]},
    )
    assert refused.status_code == 400
    assert refused.json()["error"]["code"] == "game.too_late"


async def test_a_quiz_without_a_pack_is_refused(client: AsyncClient, unique_suffix: str) -> None:
    """The empty game the room got stuck on must not be creatable."""
    await _register(
        client,
        email=f"nopack.{unique_suffix}@kbc.co.ke",
        name="Host",
        team=f"No pack {unique_suffix}",
    )
    session = (await client.post("/api/sessions", json={"title": "No pack"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    refused = await client.post(
        f"/api/sessions/{session['id']}/games", json={"game_key": "trivia-kenya"}
    )
    assert refused.status_code == 400, refused.text
    assert refused.json()["error"]["code"] == "game.needs_pack"

    # A game the host runs themselves still needs no pack.
    scored = await client.post(
        f"/api/sessions/{session['id']}/games", json={"game_key": "hosted-activity"}
    )
    assert scored.status_code == 200, scored.text


async def test_starting_a_game_replaces_the_one_that_was_running(
    client: AsyncClient, unique_suffix: str
) -> None:
    """One meeting, one live game: the room must never be left on a stale one."""
    await _register(
        client,
        email=f"replace.{unique_suffix}@kbc.co.ke",
        name="Host",
        team=f"Replace {unique_suffix}",
    )
    session = (await client.post("/api/sessions", json={"title": "Replace"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    first = await _quiz_play(client, session["id"])
    second = await _quiz_play(client, session["id"])

    assert (await client.get(f"/api/game-plays/{first['id']}")).json()["status"] == "abandoned"
    detail = (await client.get(f"/api/sessions/{session['id']}")).json()
    running = [game for game in detail["games"] if game["status"] == "running"]
    assert [game["id"] for game in running] == [second["id"]]

    # The room can tell who is driving the game it is following.
    assert (await client.get(f"/api/game-plays/{second['id']}")).json()["host_name"] == "Host"
