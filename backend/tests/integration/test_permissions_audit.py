"""Roles, tenancy and the audit of refused actions."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_a_refused_action_is_recorded_for_admins(
    client: AsyncClient, unique_suffix: str
) -> None:
    owner = await client.post(
        "/api/auth/register",
        json={
            "email": f"owner.{unique_suffix}@kbc.co.ke",
            "display_name": "Owner",
            "password": "a-good-password",
            "team_name": f"Roles {unique_suffix}",
        },
    )
    assert owner.status_code == 200
    owner_client_headers = dict(client.headers)

    idea = (await client.post("/api/ideas", json={"title": "Keep me"})).json()
    invite = (await client.post("/api/team/invites", json={"role": "member"})).json()

    # A member joins the same team through the invite.
    member = AsyncClient(
        transport=client._transport,  # type: ignore[attr-defined]
        base_url="http://test",
        headers=owner_client_headers,
    )
    async with member:
        joined = await member.post(
            "/api/auth/register",
            json={
                "email": f"member.{unique_suffix}@kbc.co.ke",
                "display_name": "Member",
                "password": "a-good-password",
                "invite_code": invite["code"],
            },
        )
        assert joined.status_code == 200, joined.text

        # Deleting somebody else's idea is an admin action.
        refused = await member.delete(f"/api/ideas/{idea['id']}")
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "permission_denied"

        # The idea is still there.
        assert (await member.get(f"/api/ideas/{idea['id']}")).status_code == 200

    # The owner can see that somebody tried.
    trail = (await client.get("/api/activity", params={"target_type": "permission"})).json()
    verbs = [item["verb"] for item in trail["items"]]
    assert "permission.denied" in verbs
