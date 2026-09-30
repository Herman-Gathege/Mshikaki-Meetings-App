"""The rehearsal: one complete meeting, start to finish, over real HTTP.

This is the test that matters most. It walks the loop the product exists to
support and asserts the promises made about it:

  create session -> capture ideas -> record a decision -> assign tasks ->
  play a game -> close -> summary -> traceability -> audit trail.

If this passes, a team can genuinely run a meeting in Mshikaki.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def register_team(client: AsyncClient, suffix: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": f"herman.{suffix}@example.com",
            "display_name": "Herman",
            "password": "a-good-password",
            "team_name": "Innovations",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_whole_meeting_loop(client: AsyncClient, unique_suffix: str) -> None:
    identity = await register_team(client, unique_suffix)
    assert identity["role"] == "owner"

    # 1. Plan the meeting.
    created = await client.post(
        "/api/sessions",
        json={
            "scheduled_at": "2026-10-01T09:00:00Z",
            "location": "Boardroom",
            "agenda": ["Icebreaker", "Automation ideas", "Assignments"],
        },
    )
    assert created.status_code == 200, created.text
    session = created.json()
    session_id = session["id"]
    assert session["sequence_no"] == 1
    assert [item["title"] for item in session["agenda"]] == [
        "Icebreaker",
        "Automation ideas",
        "Assignments",
    ]

    # 2. Start it. A second live session must be refused.
    started = await client.post(f"/api/sessions/{session_id}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "active"

    second = await client.post("/api/sessions", json={"title": "Another meeting"})
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "session.already_active"

    # 3. Mark attendance.
    participants = (await client.get(f"/api/sessions/{session_id}/participants")).json()
    assert participants["total"] >= 1
    me_id = participants["items"][0]["id"]
    attendance = await client.patch(
        f"/api/sessions/{session_id}/participants/{me_id}", json={"attended": True}
    )
    assert attendance.status_code == 200

    # 4. Capture an idea mid-discussion, the way a person would from a phone.
    idea_response = await client.post(
        "/api/ideas",
        json={"title": "Automate radio schedule notifications", "session_id": session_id},
    )
    assert idea_response.status_code == 200, idea_response.text
    idea = idea_response.json()

    # 5. Discuss it, then accept it.
    discussing = await client.patch(f"/api/ideas/{idea['id']}", json={"status": "discussing"})
    assert discussing.status_code == 200
    accepted = await client.patch(f"/api/ideas/{idea['id']}", json={"status": "accepted"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    # 6. Record the decision it produced. The idea is promoted automatically.
    decision_response = await client.post(
        "/api/decisions",
        json={
            "statement": "Proceed with automated radio schedule notifications.",
            "session_id": session_id,
            "idea_id": idea["id"],
        },
    )
    assert decision_response.status_code == 200, decision_response.text
    decision = decision_response.json()

    promoted = await client.get(f"/api/ideas/{idea['id']}")
    assert promoted.json()["status"] == "converted"
    assert promoted.json()["converted_to"]["type"] == "decision"

    # 7. Turn the decision into assigned work.
    task_response = await client.post(
        "/api/tasks",
        json={
            "title": "Draft the notification spec",
            "owner_id": identity["user"]["id"],
            "session_id": session_id,
            "decision_id": decision["id"],
            "status": "backlog",
            "priority": "high",
            "due_date": "2026-10-08",
        },
    )
    assert task_response.status_code == 200, task_response.text
    task = task_response.json()
    assert task["origin"]["session_id"] == session_id
    assert task["origin"]["decision_id"] == decision["id"]

    # 8. A task cannot start without an owner, and cannot be blocked without one.
    in_progress = await client.post(
        f"/api/tasks/{task['id']}/status", json={"status": "in_progress"}
    )
    assert in_progress.status_code == 200

    # 9. Block it, then put the fire out.
    blocker_response = await client.post(
        f"/api/tasks/{task['id']}/blockers", json={"reason": "Waiting on the vendor API"}
    )
    assert blocker_response.status_code == 200, blocker_response.text
    assert blocker_response.json()["status"] == "blocked"
    blocker_id = blocker_response.json()["blocker"]["id"]

    resolved = await client.post(
        f"/api/blockers/{blocker_id}/resolve", json={"resolution": "Vendor sent credentials"}
    )
    assert resolved.status_code == 200
    after = await client.get(f"/api/tasks/{task['id']}")
    assert after.json()["status"] == "in_progress"

    # 10. Play a game. The host paces it and keeps score.
    games = (await client.get("/api/games")).json()["items"]
    assert any(game["family"] == "host_quiz" for game in games)
    packs = (await client.get("/api/games/packs", params={"family": "host_quiz"})).json()
    assert packs["items"], "the content packs must be seeded for a game to be playable"

    play_response = await client.post(
        f"/api/sessions/{session_id}/games",
        json={"game_key": "trivia-kenya", "content_pack_id": packs["items"][0]["id"]},
    )
    assert play_response.status_code == 200, play_response.text
    play = play_response.json()
    assert play["question"] is not None

    scored = await client.post(
        f"/api/game-plays/{play['id']}/score",
        json={"user_id": identity["user"]["id"], "points": 10},
    )
    assert scored.status_code == 200
    assert scored.json()["scores"][0]["points"] == 10

    # The host is always right: a correction is allowed and recorded.
    corrected = await client.post(
        f"/api/game-plays/{play['id']}/override",
        json={"user_id": identity["user"]["id"], "points": 15, "reason": "counted twice"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["scores"][0]["points"] == 15

    finished = await client.post(f"/api/game-plays/{play['id']}/finish")
    assert finished.status_code == 200
    assert finished.json()["status"] == "finished"

    # 11. Finish the work.
    done = await client.post(f"/api/tasks/{task['id']}/status", json={"status": "done"})
    assert done.status_code == 200

    # 12. Close the meeting. The summary is generated, not written by a human.
    closed = await client.post(f"/api/sessions/{session_id}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "completed"
    assert closed.json()["has_summary"] is True

    summary = (await client.get(f"/api/sessions/{session_id}/summary")).json()
    counts = summary["summary"]["counts"]
    assert counts["ideas"] == 1
    assert counts["decisions"] == 1
    assert counts["tasks_created"] == 1
    assert counts["games"] == 1

    text = summary["text"]
    assert "Proceed with automated radio schedule notifications." in text
    assert "Draft the notification spec" in text
    assert "Herman" in text

    exported = await client.get(f"/api/sessions/{session_id}/export.txt")
    assert exported.status_code == 200
    assert "Decisions (1)" in exported.text

    # 13. Traceability: why does this task exist?
    task_detail = (await client.get(f"/api/tasks/{task['id']}")).json()
    assert task_detail["origin"]["decision_id"] == decision["id"]
    decision_detail = (await client.get(f"/api/decisions/{decision['id']}")).json()
    assert decision_detail["idea_id"] == idea["id"]
    assert decision_detail["session_id"] == session_id

    # 14. The audit trail recorded all of it, in order, attributed.
    trail = (await client.get(f"/api/sessions/{session_id}/activity")).json()["items"]
    verbs = [item["verb"] for item in trail]
    for expected in (
        "session.started",
        "idea.created",
        "idea.status_changed",
        "decision.recorded",
        "task.created",
        "blocker.raised",
        "blocker.resolved",
        "game.finished",
        "session.closed",
    ):
        assert expected in verbs, f"{expected} missing from the audit trail"
    assert all(item["actor_name"] for item in trail)
    assert any("Automate radio schedule" in item["sentence"] for item in trail)

    # 15. Bragging rights were settled, and the leaderboard is readable.
    leaderboard = (await client.get("/api/leaderboard", params={"scope": "season"})).json()
    assert leaderboard["items"], "someone should have earned XP for that meeting"
    assert "Not a performance measure" in leaderboard["disclaimer"]

    metrics = (await client.get("/api/metrics")).json()
    assert metrics["completed"] >= 1
    assert "not a ranking" in metrics["note"]


async def test_tenancy_isolation(client: AsyncClient, unique_suffix: str) -> None:
    """A second team's data must be invisible, and reported as missing."""
    await register_team(client, f"a{unique_suffix}")
    first_session = (await client.post("/api/sessions", json={"title": "Team A"})).json()

    await register_team(client, f"b{unique_suffix}")
    # Registering signs the new user in, so this request is now team B.
    other = await client.get(f"/api/sessions/{first_session['id']}")
    assert other.status_code == 404
    listing = (await client.get("/api/sessions")).json()
    assert all(item["id"] != first_session["id"] for item in listing["items"]), (
        "team B must not see team A's sessions"
    )


async def test_mutations_require_the_csrf_header(app, unique_suffix: str) -> None:
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as bare:
        response = await bare.post(
            "/api/auth/register",
            json={
                "email": f"csrf.{unique_suffix}@example.com",
                "display_name": "No Header",
                "password": "a-good-password",
            },
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "request.untrusted"
