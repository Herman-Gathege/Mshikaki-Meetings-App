"""The game lifecycle, the minutes, and the promises around both."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def register(client: AsyncClient, suffix: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": f"host.{suffix}@kbc.co.ke",
            "display_name": "Host",
            "password": "a-good-password",
            "team_name": f"Innovations {suffix}",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def open_session(client: AsyncClient, suffix: str) -> str:
    session = (
        await client.post(
            "/api/sessions",
            json={"title": f"Weekly {suffix}", "agenda": ["Warm up", "Ideas", "Assignments"]},
        )
    ).json()
    started = await client.post(f"/api/sessions/{session['id']}/start")
    assert started.status_code == 200
    return session["id"]


async def test_question_lifecycle_and_scoring(client: AsyncClient, unique_suffix: str) -> None:
    identity = await register(client, unique_suffix)
    session_id = await open_session(client, unique_suffix)

    packs = (await client.get("/api/games/packs", params={"family": "host_quiz"})).json()["items"]
    kenya = next(pack for pack in packs if pack["game_key"] == "trivia-kenya")
    play = (
        await client.post(
            f"/api/sessions/{session_id}/games",
            json={"game_key": "trivia-kenya", "content_pack_id": kenya["id"]},
        )
    ).json()

    # A question a room can actually play: a prompt, options, and the answer.
    assert play["question"]["prompt"]
    assert len(play["question"]["choices"]) >= 2
    assert play["question"]["answer"]
    assert play["index"] == 0
    assert play["total"] > 1

    # Next advances, previous goes back, and the pack survives the round trip.
    advanced = (await client.post(f"/api/game-plays/{play['id']}/next")).json()
    assert advanced["index"] == 1
    assert advanced["question"]["prompt"] != play["question"]["prompt"]
    back = (await client.post(f"/api/game-plays/{play['id']}/previous")).json()
    assert back["index"] == 0

    # The host scores the players who got it right.
    await client.post(
        f"/api/game-plays/{play['id']}/score",
        json={"user_id": identity["user"]["id"], "points": 10},
    )
    corrected = (
        await client.post(
            f"/api/game-plays/{play['id']}/override",
            json={"user_id": identity["user"]["id"], "points": 15, "reason": "counted twice"},
        )
    ).json()
    assert corrected["scores"][0]["points"] == 15

    finished = (await client.post(f"/api/game-plays/{play['id']}/finish")).json()
    assert finished["status"] == "finished"
    assert finished["scores"][0]["position"] == 1

    # Finishing twice must not pay twice: XP is a ledger with idempotent awards.
    points_once = (await client.get("/api/me/points")).json()["season"]["points"]
    await client.post(f"/api/game-plays/{play['id']}/finish")
    points_twice = (await client.get("/api/me/points")).json()["season"]["points"]
    assert points_twice == points_once


async def test_session_can_pause_resume_and_cancel(client: AsyncClient, unique_suffix: str) -> None:
    await register(client, f"p{unique_suffix}")
    session_id = await open_session(client, f"p{unique_suffix}")

    paused = (await client.post(f"/api/sessions/{session_id}/pause")).json()
    assert paused["status"] == "paused"
    resumed = (await client.post(f"/api/sessions/{session_id}/resume")).json()
    assert resumed["status"] == "active"

    # Only one meeting runs at a time, which is a product rule worth protecting.
    refused = await client.post("/api/sessions", json={"title": "Second"})
    assert refused.status_code == 400
    assert refused.json()["error"]["code"] == "session.already_active"

    closed = (await client.post(f"/api/sessions/{session_id}/close")).json()
    assert closed["status"] == "completed"

    # With nothing running, a new meeting can be planned.
    other = (await client.post("/api/sessions", json={"title": "Second"})).json()
    assert other["status"] == "planned"
    assert other["sequence_no"] == 2

    # And a meeting that will not happen can be cancelled, with a reason in the record.
    cancelled = (
        await client.post(
            f"/api/sessions/{other['id']}/cancel",
            json={"reason": "Half the team is in the field"},
        )
    ).json()
    assert cancelled["status"] == "cancelled"

    trail = (await client.get(f"/api/sessions/{other['id']}/activity")).json()["items"]
    cancellation = next(item for item in trail if item["verb"] == "session.cancelled")
    assert "Half the team is in the field" in cancellation["sentence"]

    # A cancelled meeting must not block the next one.
    after = (await client.post("/api/sessions", json={"title": "Third"})).json()
    assert after["status"] == "planned"


async def test_minutes_are_frozen_complete_and_downloadable(
    client: AsyncClient, unique_suffix: str
) -> None:
    identity = await register(client, f"m{unique_suffix}")
    session_id = await open_session(client, f"m{unique_suffix}")
    participants = (await client.get(f"/api/sessions/{session_id}/participants")).json()["items"]
    await client.patch(
        f"/api/sessions/{session_id}/participants/{participants[0]['id']}",
        json={"attended": True},
    )

    idea = (
        await client.post(
            "/api/ideas", json={"title": "Automate the mixer", "session_id": session_id}
        )
    ).json()
    decision = (
        await client.post(
            "/api/decisions",
            json={
                "statement": "Proceed with automation.",
                "session_id": session_id,
                "idea_id": idea["id"],
            },
        )
    ).json()
    await client.post(
        "/api/tasks",
        json={
            "title": "Write the spec",
            "owner_id": identity["user"]["id"],
            "session_id": session_id,
            "decision_id": decision["id"],
            "status": "in_progress",
        },
    )

    # Minutes before the meeting closes would be a different document every time.
    too_early = await client.get(f"/api/sessions/{session_id}/minutes.html")
    assert too_early.status_code == 400
    assert too_early.json()["error"]["code"] == "minutes.not_closed"

    closed = (await client.post(f"/api/sessions/{session_id}/close")).json()
    assert closed["status"] == "completed"
    assert closed["has_summary"] is True

    minutes = await client.get(f"/api/sessions/{session_id}/minutes.html")
    assert minutes.status_code == 200
    assert "text/html" in minutes.headers["content-type"]
    assert "attachment" in minutes.headers["content-disposition"]
    html = minutes.text
    for section in (
        "MSHIKAKI MEETING MINUTES",
        "1. Meeting details",
        "2. Agenda",
        "3. Opening and play",
        "4. Ideas raised",
        "5. Decisions made",
        "6. Action items",
        "7. Blockers",
        "8. Closing summary",
        "9. Record information",
    ):
        assert section in html, f"{section} missing from the minutes"
    assert "Proceed with automation." in html
    assert "Write the spec" in html
    assert "Warm up" in html  # the agenda recorded on the meeting

    # The WhatsApp export the team actually pastes stays available.
    text = await client.get(f"/api/sessions/{session_id}/export.txt")
    assert text.status_code == 200
    assert "Proceed with automation." in text.text

    # Downloading does not rewrite the record.
    again = await client.get(f"/api/sessions/{session_id}/summary")
    assert (
        again.json()["generated_at"]
        == (await client.get(f"/api/sessions/{session_id}/summary")).json()["generated_at"]
    )
