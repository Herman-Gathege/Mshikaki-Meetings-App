"""Scanning the code when you already have an account.

The user test found that somebody who had joined before was missing from the
attendance list: only the sign-up path ever added a participant row. These tests
hold the fixed behaviour -- one account, and you can put yourself in the meeting.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, payload: dict) -> dict:
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _second_client(client: AsyncClient) -> AsyncClient:
    return AsyncClient(
        transport=client._transport,  # type: ignore[attr-defined]
        base_url="http://test",
        headers=dict(client.headers),
    )


async def test_a_member_with_an_account_can_join_and_is_counted(
    client: AsyncClient, unique_suffix: str
) -> None:
    await _register(
        client,
        {
            "email": f"host.{unique_suffix}@kbc.co.ke",
            "display_name": "Herman",
            "password": "a-good-password",
            "team_name": f"Join {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Weekly", "agenda": ["A"]})).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    invite = (await client.post("/api/team/invites", json={"role": "member"})).json()
    async with _second_client(client) as anne:
        joined = await _register(
            anne,
            {
                "email": f"anne.{unique_suffix}@kbc.co.ke",
                "display_name": "Anne",
                "password": "a-good-password",
                "invite_code": invite["code"],
            },
        )
        # She has an account and is in the team, but the meeting started after
        # that, so she is not in the room yet.
        before = (await client.get(f"/api/sessions/{session['id']}/participants")).json()
        assert [row["name"] for row in before["items"]] == ["Herman"]

        # She scans the code again: no new account, and she lands in the record.
        landing = await anne.post(f"/api/sessions/{session['id']}/join")
        assert landing.status_code == 200, landing.text
        assert landing.json()["id"] == session["id"]

        after = (await client.get(f"/api/sessions/{session['id']}/participants")).json()
        names = [row["name"] for row in after["items"]]
        assert names == ["Anne", "Herman"] or names == ["Herman", "Anne"]
        anne_row = next(row for row in after["items"] if row["name"] == "Anne")
        assert anne_row["user_id"] == joined["user"]["id"]
        assert anne_row["attended"] is True

        trail = (await client.get("/api/sessions/" + session["id"] + "/activity")).json()
        assert "session.participant_joined" in [item["verb"] for item in trail["items"]]

        # Scanning twice is not two people and not two entries.
        again = await anne.post(f"/api/sessions/{session['id']}/join")
        assert again.status_code == 200
        participants = (await client.get(f"/api/sessions/{session['id']}/participants")).json()
        assert participants["total"] == 2


async def test_joining_is_refused_when_the_meeting_is_not_open(
    client: AsyncClient, unique_suffix: str
) -> None:
    await _register(
        client,
        {
            "email": f"host2.{unique_suffix}@kbc.co.ke",
            "display_name": "Herman",
            "password": "a-good-password",
            "team_name": f"Closed {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Finished"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")
    await client.post(f"/api/sessions/{session['id']}/close")

    refused = await client.post(f"/api/sessions/{session['id']}/join")
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "permission_denied"


async def test_a_meeting_in_another_team_is_invisible(
    client: AsyncClient, unique_suffix: str
) -> None:
    await _register(
        client,
        {
            "email": f"other.{unique_suffix}@kbc.co.ke",
            "display_name": "Other",
            "password": "a-good-password",
            "team_name": f"Team A {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Ours"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    async with _second_client(client) as stranger:
        await _register(
            stranger,
            {
                "email": f"stranger.{unique_suffix}@kbc.co.ke",
                "display_name": "Stranger",
                "password": "a-good-password",
                "team_name": f"Team B {unique_suffix}",
            },
        )
        hidden = await stranger.post(f"/api/sessions/{session['id']}/join")
        assert hidden.status_code == 404
