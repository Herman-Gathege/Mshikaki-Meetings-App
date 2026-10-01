"""Run Mode: one facilitator drives, everybody follows, and everybody is released.

The authoritative stage lives on the session, so these tests check the state that
every other client converges on rather than any single browser's behaviour.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_starting_a_meeting_puts_the_room_in_run_mode(
    client: AsyncClient, unique_suffix: str
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"sync.{unique_suffix}@kbc.co.ke",
            "display_name": "Sync Host",
            "password": "a-good-password",
            "team_name": f"Sync {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Running"})).json()
    assert session["run_mode_stage"] is None
    assert session["run_mode_active"] is False

    started = (await client.post(f"/api/sessions/{session['id']}/start")).json()
    assert started["status"] == "active"
    assert started["run_mode_stage"] == "play"
    assert started["run_mode_active"] is True


async def test_the_facilitator_moves_the_room_and_the_stage_persists(
    client: AsyncClient, unique_suffix: str
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"move.{unique_suffix}@kbc.co.ke",
            "display_name": "Mover",
            "password": "a-good-password",
            "team_name": f"Move {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Moving"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    for stage in ("capture", "decide", "assign", "close"):
        moved = (
            await client.post(f"/api/sessions/{session['id']}/run-mode", json={"stage": stage})
        ).json()
        assert moved["run_mode_stage"] == stage

    # A participant reading the session sees where the room is, not where they left it.
    fresh = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert fresh["run_mode_stage"] == "close"
    assert fresh["run_mode_active"] is True


async def test_closing_the_meeting_releases_everybody(
    client: AsyncClient, unique_suffix: str
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"wrap.{unique_suffix}@kbc.co.ke",
            "display_name": "Wrapper",
            "password": "a-good-password",
            "team_name": f"Wrap {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Wrapping"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")
    await client.post(f"/api/sessions/{session['id']}/run-mode", json={"stage": "close"})

    closed = (await client.post(f"/api/sessions/{session['id']}/close")).json()

    assert closed["status"] == "completed"
    assert closed["run_mode_stage"] is None, "the room must not stay trapped in Run Mode"
    assert closed["run_mode_active"] is False


async def test_only_the_facilitator_moves_the_room(client: AsyncClient, unique_suffix: str) -> None:
    """A participant follows. They do not steer."""
    owner = await client.post(
        "/api/auth/register",
        json={
            "email": f"host.{unique_suffix}@kbc.co.ke",
            "display_name": "Host",
            "password": "a-good-password",
            "team_name": f"Steering {unique_suffix}",
        },
    )
    assert owner.status_code == 200
    session = (await client.post("/api/sessions", json={"title": "Steered"})).json()
    invite = (await client.post("/api/team/invites", json={"role": "member"})).json()

    participant = AsyncClient(
        transport=client._transport,  # type: ignore[attr-defined]
        base_url="http://test",
        headers=dict(client.headers),
    )
    async with participant:
        joined = await participant.post(
            "/api/auth/register",
            json={
                "email": f"member.{unique_suffix}@kbc.co.ke",
                "display_name": "Member",
                "password": "a-good-password",
                "invite_code": invite["code"],
            },
        )
        assert joined.status_code == 200

        await client.post(f"/api/sessions/{session['id']}/start")

        # They can read where the room is.
        followed = (await participant.get(f"/api/sessions/{session['id']}")).json()
        assert followed["run_mode_stage"] == "play"

        # But they cannot move it.
        refused = await participant.post(
            f"/api/sessions/{session['id']}/run-mode", json={"stage": "decide"}
        )
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "permission_denied"

        still = (await client.get(f"/api/sessions/{session['id']}")).json()
        assert still["run_mode_stage"] == "play", "a participant moved the meeting"


async def test_an_unknown_stage_is_refused_clearly(client: AsyncClient, unique_suffix: str) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"badstage.{unique_suffix}@kbc.co.ke",
            "display_name": "Bad Stage",
            "password": "a-good-password",
            "team_name": f"Badstage {unique_suffix}",
        },
    )
    session = (await client.post("/api/sessions", json={"title": "Bad"})).json()
    await client.post(f"/api/sessions/{session['id']}/start")

    response = await client.post(
        f"/api/sessions/{session['id']}/run-mode", json={"stage": "teleport"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "run_mode.bad_stage"
