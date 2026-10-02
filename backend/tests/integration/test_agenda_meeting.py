"""A serious meeting: the agenda carries the room, and the record keeps up.

No game is played. The facilitator opens the meeting, walks the agenda, and the
summary at the end has to read like minutes rather than a database dump.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, *, email: str, name: str, team: str):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "display_name": name,
            "password": "a-good-password",
            "team_name": team,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _meeting(client: AsyncClient, unique_suffix: str) -> dict:
    """A started meeting with four agenda items and a colleague in the room."""
    await _register(
        client,
        email=f"chair.{unique_suffix}@kbc.co.ke",
        name="Herman",
        team=f"Agenda {unique_suffix}",
    )
    session = (
        await client.post(
            "/api/sessions",
            json={
                "title": f"Operations review {unique_suffix}",
                "agenda": [
                    "Q4 project progress",
                    "Website launch",
                    "Budget approval",
                    "Next steps",
                ],
            },
        )
    ).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    invite = (await client.post("/api/team/invites", json={"role": "member"})).json()
    async with AsyncClient(
        transport=client._transport,  # type: ignore[attr-defined]
        base_url="http://test",
        headers=dict(client.headers),
    ) as joining:
        joined = await joining.post(
            "/api/auth/register",
            json={
                "email": f"anne.{unique_suffix}@kbc.co.ke",
                "display_name": "Anne",
                "password": "a-good-password",
                "invite_code": invite["code"],
            },
        )
    assert joined.status_code == 200, joined.text
    identity = joined.json()
    # Keep the colleague's session cookie: their second client has to be them.
    raw_cookie = joined.headers.get("set-cookie", "")
    cookie = raw_cookie.split(";")[0]
    await client.post(
        f"/api/sessions/{session['id']}/participants",
        json={"user_id": identity["user"]["id"], "role": "participant"},
    )
    return {
        "session": session,
        "identity": identity,
        "transport": client._transport,  # type: ignore[attr-defined]
        "headers": dict(client.headers),
        "cookie": cookie,
    }


def _colleague(meeting: dict) -> AsyncClient:
    """A second person in the same room, with their own session cookie."""
    headers = dict(meeting["headers"])
    if meeting.get("cookie"):
        headers["cookie"] = meeting["cookie"]
    return AsyncClient(transport=meeting["transport"], base_url="http://test", headers=headers)


async def test_a_serious_meeting_walks_the_agenda_without_a_game(
    client: AsyncClient, unique_suffix: str
) -> None:
    meeting = await _meeting(client, unique_suffix)
    session_id = meeting["session"]["id"]

    async with _colleague(meeting) as colleague:
        # The opening choice: straight to the meeting, no game.
        started = await client.post(f"/api/sessions/{session_id}/meeting/start")
        assert started.status_code == 200, started.text
        detail = started.json()
        assert detail["run_mode_stage"] == "agenda"
        assert detail["agenda_position"] == {
            "position": 1,
            "total": 4,
            "remaining": 3,
            "is_last": False,
        }
        assert detail["agenda"][0]["is_current"] is True
        current_id = detail["current_agenda_item_id"]
        assert current_id == detail["agenda"][0]["id"]

        # A participant sees the same item, and cannot move the room.
        seen = (await colleague.get(f"/api/sessions/{session_id}")).json()
        assert seen["current_agenda_item_id"] == current_id
        assert seen["run_mode_stage"] == "agenda"
        refused = await colleague.post(f"/api/sessions/{session_id}/agenda/next")
        assert refused.status_code == 403

        # Anybody can note something under the item being discussed.
        note = await colleague.post(
            f"/api/sessions/{session_id}/notes",
            json={
                "body": "Finance will confirm the final figure tomorrow.",
                "agenda_item_id": current_id,
            },
        )
        assert note.status_code == 200, note.text
        assert note.json()["agenda_item_id"] == current_id

        # An idea and a decision hang off the same item.
        idea = (
            await colleague.post(
                "/api/ideas",
                json={
                    "title": "Automate the monthly report",
                    "session_id": session_id,
                    "agenda_item_id": current_id,
                },
            )
        ).json()
        decision = (
            await client.post(
                "/api/decisions",
                json={
                    "statement": "Proceed with the website launch plan.",
                    "session_id": session_id,
                    "agenda_item_id": current_id,
                    "idea_id": idea["id"],
                },
            )
        ).json()

        # One meaningful action, not five.
        task = (
            await client.post(
                "/api/tasks",
                json={
                    "title": "Prepare the final launch checklist",
                    "owner_id": meeting["identity"]["user"]["id"],
                    "session_id": session_id,
                    "agenda_item_id": current_id,
                    "decision_id": decision["id"],
                },
            )
        ).json()
        assert task["id"]

        # How the item ended, in one word.
        outcome = await client.post(
            f"/api/sessions/{session_id}/agenda/{current_id}/outcome",
            json={"outcome": "assigned"},
        )
        assert outcome.status_code == 200, outcome.text
        assert outcome.json()["agenda"][0]["outcome"] == "assigned"

        # Next agenda moves the room, and the item is marked covered.
        moved = (await client.post(f"/api/sessions/{session_id}/agenda/next")).json()
        assert moved["agenda_position"]["position"] == 2
        assert moved["agenda"][0]["covered"] is True
        assert moved["agenda"][1]["is_current"] is True
        assert moved["run_mode_stage"] == "agenda"

        # Walk the rest, then the agenda hands the room to the wrap.
        for _ in range(3):
            moved = (await client.post(f"/api/sessions/{session_id}/agenda/next")).json()
        assert moved["run_mode_stage"] == "close"
        assert moved["current_agenda_item_id"] is None
        assert moved["agenda_position"]["position"] == 0

        closed = await client.post(f"/api/sessions/{session_id}/close")
        assert closed.status_code == 200, closed.text

        # The minutes read like minutes.
        summary = (await client.get(f"/api/sessions/{session_id}/summary")).json()["summary"]
        titles = [item["title"] for item in summary["agenda"]]
        assert titles == ["Q4 project progress", "Website launch", "Budget approval", "Next steps"]
        assert summary["notes"][0]["body"].startswith("Finance will confirm")
        assert summary["notes"][0]["agenda_title"] == "Q4 project progress"
        assert summary["ideas"][0]["agenda_title"] == "Q4 project progress"
        assert summary["decisions"][0]["agenda_title"] == "Q4 project progress"
        assert summary["tasks_created"][0]["agenda_title"] == "Q4 project progress"
        assert summary["counts"]["notes"] == 1
        assert summary["counts"]["agenda_items"] == 4

        html = await client.get(f"/api/sessions/{session_id}/minutes.html")
        assert html.status_code == 200
        for expected in (
            "Q4 project progress",
            "Finance will confirm the final figure tomorrow.",
            "Proceed with the website launch plan.",
            "Prepare the final launch checklist",
            "Notes kept",
        ):
            assert expected in html.text, f"{expected} missing from the minutes"

        text = await client.get(f"/api/sessions/{session_id}/export.txt")
        assert "Finance will confirm the final figure tomorrow." in text.text

        # PDF, printable and self-describing.
        pdf = await client.get(f"/api/sessions/{session_id}/summary.pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF-")
        assert len(pdf.content) > 3000


async def test_agenda_survives_a_game_and_never_goes_backwards(
    client: AsyncClient, unique_suffix: str
) -> None:
    """The playful journey and the serious one share one meeting."""
    meeting = await _meeting(client, unique_suffix)
    session_id = meeting["session"]["id"]

    # Play first, then the meeting starts where it left off.
    packs = (await client.get("/api/games/packs", params={"family": "host_quiz"})).json()["items"]
    pack = next(p for p in packs if p["game_key"] == "trivia-kenya")
    play = (
        await client.post(
            f"/api/sessions/{session_id}/games",
            json={"game_key": "trivia-kenya", "content_pack_id": pack["id"]},
        )
    ).json()
    assert play["status"] == "running"

    opened = (await client.post(f"/api/sessions/{session_id}/meeting/start")).json()
    assert opened["run_mode_stage"] == "agenda"
    assert opened["agenda_position"]["position"] == 1
    first = opened["current_agenda_item_id"]

    second = (await client.post(f"/api/sessions/{session_id}/agenda/next")).json()
    assert second["agenda_position"]["position"] == 2

    # Coming back to the agenda after a detour must not restart the meeting.
    again = (
        await client.post(f"/api/sessions/{session_id}/run-mode", json={"stage": "agenda"})
    ).json()
    assert again["agenda_position"]["position"] == 2
    assert again["current_agenda_item_id"] == second["current_agenda_item_id"]

    # A facilitator correction is allowed and explicit.
    back = (await client.post(f"/api/sessions/{session_id}/agenda/{first}/current")).json()
    assert back["agenda_position"]["position"] == 1


async def test_an_unknown_outcome_is_refused_clearly(
    client: AsyncClient, unique_suffix: str
) -> None:
    meeting = await _meeting(client, unique_suffix)
    session_id = meeting["session"]["id"]
    opened = (await client.post(f"/api/sessions/{session_id}/meeting/start")).json()
    item_id = opened["current_agenda_item_id"]

    refused = await client.post(
        f"/api/sessions/{session_id}/agenda/{item_id}/outcome", json={"outcome": "pendingish"}
    )
    assert refused.status_code == 400
    assert refused.json()["error"]["code"] == "agenda.bad_outcome"
