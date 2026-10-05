"""Notes that can be edited, given to somebody, and marked where they got to."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _room(client: AsyncClient, suffix: str) -> dict:
    """A running meeting with Herman (facilitator) and Anne in it."""
    host = await client.post(
        "/api/auth/register",
        json={
            "email": f"host.{suffix}@kbc.co.ke",
            "display_name": "Herman",
            "password": "a-good-password",
            "team_name": f"Notes {suffix}",
        },
    )
    assert host.status_code == 200, host.text
    session = (
        await client.post("/api/sessions", json={"title": "Notes", "agenda": ["Budget"]})
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
                "email": f"anne.{suffix}@kbc.co.ke",
                "display_name": "Anne",
                "password": "a-good-password",
                "invite_code": invite["code"],
            },
        )
    identity = joined.json()
    # The cookie is what makes the second client Anne, and a client is only
    # opened once, so the test builds its own from these.
    cookie = joined.headers.get("set-cookie", "").split(";")[0]
    await client.post(
        f"/api/sessions/{session['id']}/participants",
        json={"user_id": identity["user"]["id"], "role": "participant"},
    )
    opened = (await client.post(f"/api/sessions/{session['id']}/meeting/start")).json()
    return {
        "session": session,
        "anne_id": identity["user"]["id"],
        "item": opened["current_agenda_item_id"],
        "cookie": cookie,
        "headers": dict(client.headers),
        "transport": client._transport,  # type: ignore[attr-defined]
    }


def _anne(room: dict) -> AsyncClient:
    headers = dict(room["headers"])
    headers["cookie"] = room["cookie"]
    return AsyncClient(transport=room["transport"], base_url="http://test", headers=headers)


async def test_a_note_can_be_given_to_somebody_by_naming_them(
    client: AsyncClient, unique_suffix: str
) -> None:
    room = await _room(client, unique_suffix)
    async with _anne(room) as anne:  # noqa: F841 - the client is the point of the context
        note = (
            await anne.post(
                f"/api/sessions/{room['session']['id']}/notes",
                json={
                    "body": "@Anne please chase the invoice before Friday.",
                    "agenda_item_id": room["item"],
                },
            )
        ).json()
        assert note["mentions"] == [{"id": room["anne_id"], "name": "Anne"}]
        assert note["assignee_name"] == "Anne", "naming somebody gives them the note"
        assert note["status"] == "open"


async def test_a_note_can_be_edited_assigned_and_marked(
    client: AsyncClient, unique_suffix: str
) -> None:
    room = await _room(client, unique_suffix)
    async with _anne(room) as anne:  # noqa: F841 - the client is the point of the context
        note = (
            await client.post(
                f"/api/sessions/{room['session']['id']}/notes",
                json={"body": "Finance confirms tomorrow.", "agenda_item_id": room["item"]},
            )
        ).json()
        assert note["assignee_id"] is None

        edited = await client.patch(
            f"/api/sessions/{room['session']['id']}/notes/{note['id']}",
            json={"body": "Finance confirms the figure tomorrow at ten."},
        )
        assert edited.status_code == 200, edited.text
        assert edited.json()["body"].endswith("at ten.")
        assert edited.json()["edited"] is True

        assigned = await client.patch(
            f"/api/sessions/{room['session']['id']}/notes/{note['id']}",
            json={"assignee_id": room["anne_id"]},
        )
        assert assigned.json()["assignee_name"] == "Anne"

        done = await client.patch(
            f"/api/sessions/{room['session']['id']}/notes/{note['id']}",
            json={"status": "done"},
        )
        assert done.json()["status"] == "done"

        bad = await client.patch(
            f"/api/sessions/{room['session']['id']}/notes/{note['id']}",
            json={"status": "finished-ish"},
        )
        assert bad.status_code == 400
        assert bad.json()["error"]["code"] == "note.bad_status"


async def test_editing_a_note_is_on_the_trail(client: AsyncClient, unique_suffix: str) -> None:
    room = await _room(client, unique_suffix)
    async with _anne(room) as anne:  # noqa: F841 - the client is the point of the context
        note = (
            await client.post(
                f"/api/sessions/{room['session']['id']}/notes",
                json={"body": "First version.", "agenda_item_id": room["item"]},
            )
        ).json()
        await client.patch(
            f"/api/sessions/{room['session']['id']}/notes/{note['id']}",
            json={"body": "Second version."},
        )
        trail = (await client.get(f"/api/sessions/{room['session']['id']}/activity")).json()
        assert "note.updated" in [item["verb"] for item in trail["items"]]


async def test_the_room_a_note_can_be_given_to_is_the_joiner_list(
    client: AsyncClient, unique_suffix: str
) -> None:
    room = await _room(client, unique_suffix)
    async with _anne(room) as anne:  # noqa: F841 - the client is the point of the context
        listed = (await client.get(f"/api/sessions/{room['session']['id']}/participants")).json()
        names = sorted(row["name"] for row in listed["items"])
        assert names == ["Anne", "Herman"]
