"""History cannot be rewritten, even by the application's own connection."""

from __future__ import annotations

import pytest
from app.db.session import get_session_factory
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

pytestmark = pytest.mark.asyncio


async def test_activity_and_xp_rows_cannot_be_edited_or_deleted(
    client: AsyncClient, unique_suffix: str
) -> None:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": f"audit.{unique_suffix}@kbc.co.ke",
            "display_name": "Auditor",
            "password": "a-good-password",
            "team_name": f"Audit {unique_suffix}",
        },
    )
    assert response.status_code == 200

    session_id = (await client.post("/api/sessions", json={"title": "Audited"})).json()["id"]
    await client.post(f"/api/sessions/{session_id}/start")

    db = get_session_factory()()
    try:
        activity_count = db.execute(text("SELECT count(*) FROM activity")).scalar_one()
        assert activity_count > 0, "the setup should have written activity rows"

        with pytest.raises(DatabaseError) as update_error:
            db.execute(text("UPDATE activity SET actor_name = 'Somebody Else'"))
        assert "append-only" in str(update_error.value)
        db.rollback()

        with pytest.raises(DatabaseError) as delete_error:
            db.execute(text("DELETE FROM activity"))
        assert "append-only" in str(delete_error.value)
        db.rollback()

        # The XP ledger is protected the same way.
        with pytest.raises(DatabaseError):
            db.execute(text("DELETE FROM xp_events"))
        db.rollback()

        # And the record is intact after those attempts.
        assert db.execute(text("SELECT count(*) FROM activity")).scalar_one() == activity_count
        assert (
            db.execute(
                text("SELECT count(*) FROM activity WHERE actor_name = 'Somebody Else'")
            ).scalar_one()
            == 0
        )
    finally:
        db.close()
