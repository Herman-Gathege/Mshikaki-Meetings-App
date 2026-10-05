"""The room writes questions, and plays them."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_questions_from_the_room_can_be_played(
    client: AsyncClient, unique_suffix: str
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"host.{unique_suffix}@kbc.co.ke",
            "display_name": "Herman",
            "password": "a-good-password",
            "team_name": f"Questions {unique_suffix}",
        },
    )
    session = (
        await client.post("/api/sessions", json={"title": "Questions", "agenda": ["Warm up"]})
    ).json()
    await client.post(f"/api/sessions/{session['id']}/start")
    invite = (await client.post("/api/team/invites", json={"role": "member"})).json()

    async with AsyncClient(
        transport=client._transport,  # type: ignore[attr-defined]
        base_url="http://test",
        headers=dict(client.headers),
    ) as registering:
        joined = await registering.post(
            "/api/auth/register",
            json={
                "email": f"anne.{unique_suffix}@kbc.co.ke",
                "display_name": "Anne",
                "password": "a-good-password",
                "invite_code": invite["code"],
            },
        )
    identity = joined.json()
    cookie = joined.headers.get("set-cookie", "").split(";")[0]
    await client.post(
        f"/api/sessions/{session['id']}/participants",
        json={"user_id": identity["user"]["id"], "role": "participant"},
    )
    headers = dict(client.headers)
    headers["cookie"] = cookie
    anne = AsyncClient(transport=client._transport, base_url="http://test", headers=headers)  # type: ignore[attr-defined]

    async with anne:
        opened = (await client.post(f"/api/sessions/{session['id']}/meeting/start")).json()
        item = opened["current_agenda_item_id"]

        # A joiner suggests two questions, mid-meeting.
        first = await anne.post(
            f"/api/sessions/{session['id']}/questions",
            json={
                "prompt": "Which studio opened first?",
                "choices": ["A", "B", "C", "D"],
                "answer": "B",
                "agenda_item_id": item,
            },
        )
        assert first.status_code == 200, first.text
        assert first.json()["status"] == "suggested"
        assert first.json()["author"] == "Anne"
        second = await anne.post(
            f"/api/sessions/{session['id']}/questions",
            json={"prompt": "Name the old studio clock.", "answer": "The Bakery clock"},
        )
        assert second.status_code == 200

        # Everybody sees them.
        listed = (await client.get(f"/api/sessions/{session['id']}/questions")).json()
        assert [row["prompt"] for row in listed["items"]] == [
            "Which studio opened first?",
            "Name the old studio clock.",
        ]

        # The facilitator accepts one and rejects the other.
        accepted = await client.patch(
            f"/api/sessions/{session['id']}/questions/{first.json()['id']}",
            json={"status": "accepted"},
        )
        assert accepted.json()["status"] == "accepted"
        await client.patch(
            f"/api/sessions/{session['id']}/questions/{second.json()['id']}",
            json={"status": "rejected"},
        )

        # A joiner cannot accept their own question.
        refused = await anne.patch(
            f"/api/sessions/{session['id']}/questions/{first.json()['id']}",
            json={"status": "used"},
        )
        assert refused.status_code == 403

        # Playing them uses the existing game engine.
        play = await client.post(
            f"/api/sessions/{session['id']}/games",
            json={"game_key": "trivia-general", "use_session_questions": True},
        )
        assert play.status_code == 200, play.text
        body = play.json()
        assert body["question"]["prompt"] == "Which studio opened first?"
        assert body["question"]["answer"] == "B"
        assert body["total"] == 1, "only the questions still on the table are played"
