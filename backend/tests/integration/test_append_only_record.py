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
    registered = response.json()
    team_id = registered["team"]["id"]
    user_id = registered["user"]["id"]

    session_id = (await client.post("/api/sessions", json={"title": "Audited"})).json()["id"]
    await client.post(f"/api/sessions/{session_id}/start")

    db = get_session_factory()()
    try:
        # The guard has to hold on any database, including one where nobody has
        # earned anything yet. A row-level trigger only fires per row, so an empty
        # table makes these attempts succeed and the test prove nothing.
        db.execute(
            text(
                "INSERT INTO xp_events (id, team_id, user_id, subject_name, amount, "
                "reason_key, source_type, occurred_at, idempotency_key) VALUES "
                "(gen_random_uuid(), :team_id, :user_id, 'Auditor', 5, 'attend_session', "
                "'test', now(), :key)"
            ),
            {"team_id": team_id, "user_id": user_id, "key": f"audit-{unique_suffix}"},
        )
        db.commit()

        # And the triggers themselves must be there, whatever the row counts.
        triggers = db.execute(
            text(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname IN "
                "('activity_append_only', 'xp_events_append_only')"
            )
        ).scalar_one()
        assert triggers == 2, "the append-only triggers are missing"

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

        # The XP ledger is protected the same way, now that it has a row to lose.
        xp_count = db.execute(text("SELECT count(*) FROM xp_events")).scalar_one()
        assert xp_count > 0
        with pytest.raises(DatabaseError):
            db.execute(text("DELETE FROM xp_events"))
        db.rollback()

        with pytest.raises(DatabaseError):
            db.execute(text("UPDATE xp_events SET amount = 999"))
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
