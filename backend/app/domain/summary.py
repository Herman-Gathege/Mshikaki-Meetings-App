"""The session summary: the skewer.

Deterministic, ordered and rule-based. No language model is involved, so the same
meeting always produces the same summary, instantly and for free.

`build_summary` takes plain dictionaries, which keeps it testable with a fixture
and free of any database import.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

PLAYFUL_FOOTER = "🫱 Mshikaki: we came to the meeting to play. Somehow we left with tasks."


def _titles(rows: list[dict[str, Any]], key: str = "title") -> list[str]:
    return [str(row.get(key, "untitled")) for row in rows]


def build_summary(
    *,
    session: dict[str, Any],
    participants: list[dict[str, Any]],
    games: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    tasks_created: list[dict[str, Any]],
    tasks_completed: list[dict[str, Any]],
    tasks_reopened: list[dict[str, Any]],
    blockers_raised: list[dict[str, Any]],
    blockers_resolved: list[dict[str, Any]],
    xp_awards: list[dict[str, Any]],
    agenda: list[dict[str, Any]] | None = None,
    generated_at: datetime,
) -> dict[str, Any]:
    attendees = [p for p in participants if p.get("attended", True)]
    absent = [p for p in participants if not p.get("attended", True)]

    standings = sorted(xp_awards, key=lambda row: int(row.get("amount", 0)), reverse=True)

    return {
        "generated_at": generated_at.isoformat(),
        "session": {
            "title": session.get("title"),
            "sequence_no": session.get("sequence_no"),
            "scheduled_at": session.get("scheduled_at"),
            "started_at": session.get("started_at"),
            "ended_at": session.get("ended_at"),
            "facilitator": session.get("facilitator_name"),
            "location": session.get("location"),
        },
        "counts": {
            "participants": len(participants),
            "attended": len(attendees),
            "games": len(games),
            "ideas": len(ideas),
            "decisions": len(decisions),
            "tasks_created": len(tasks_created),
            "tasks_completed": len(tasks_completed),
            "blockers_raised": len(blockers_raised),
            "blockers_resolved": len(blockers_resolved),
        },
        "attendance": {
            "present": [p.get("name") for p in attendees],
            "absent": [p.get("name") for p in absent],
        },
        "games": games,
        "agenda": agenda or [],
        "ideas": ideas,
        "decisions": decisions,
        "tasks_created": tasks_created,
        "tasks_completed": tasks_completed,
        "tasks_reopened": tasks_reopened,
        "blockers": {"raised": blockers_raised, "resolved": blockers_resolved},
        "xp": {"awards": xp_awards, "standings": standings[:5]},
    }


def render_text(summary: dict[str, Any]) -> str:
    """Plain text built for pasting into WhatsApp. That is where teams share."""
    session = summary.get("session", {})
    counts = summary.get("counts", {})
    attendance = summary.get("attendance", {})
    lines: list[str] = []

    title = session.get("title") or "Session"
    when = session.get("scheduled_at") or session.get("started_at") or ""
    lines.append(f"*{title}*")
    if when:
        lines.append(str(when))
    if session.get("facilitator"):
        lines.append(f"Facilitated by {session['facilitator']}")
    lines.append("")

    present = [name for name in attendance.get("present", []) if name]
    if present:
        lines.append(f"*Present:* {', '.join(present)}")
    absent = [name for name in attendance.get("absent", []) if name]
    if absent:
        lines.append(f"*Absent:* {', '.join(absent)}")
    lines.append("")

    games = summary.get("games") or []
    if games:
        lines.append("*Games*")
        for game in games:
            winner = game.get("winner") or "no winner"
            lines.append(f"- {game.get('name', 'Game')}: {winner} 🏆")
        lines.append("")

    ideas = summary.get("ideas") or []
    if ideas:
        lines.append(f"*Ideas ({len(ideas)})*")
        for idea in ideas:
            author = idea.get("author") or "someone"
            status = idea.get("status") or "new"
            lines.append(f"- {idea.get('title', 'untitled')} ({author}, {status})")
        lines.append("")

    decisions = summary.get("decisions") or []
    if decisions:
        lines.append(f"*Decisions ({len(decisions)})*")
        for decision in decisions:
            lines.append(f"- {decision.get('statement', 'untitled')}")
        lines.append("")

    tasks = summary.get("tasks_created") or []
    if tasks:
        lines.append(f"*Tasks ({len(tasks)})*")
        for task in tasks:
            owner = task.get("owner") or "unassigned"
            due = task.get("due_date")
            suffix = f" - due {due}" if due else ""
            lines.append(f"- {task.get('title', 'untitled')} → {owner}{suffix}")
        lines.append("")

    raised = (summary.get("blockers") or {}).get("raised") or []
    resolved = (summary.get("blockers") or {}).get("resolved") or []
    if raised or resolved:
        lines.append("*Blockers*")
        for blocker in raised:
            lines.append(
                f"- Raised on {blocker.get('title', 'a task')}: {blocker.get('reason', '')}"
            )
        for blocker in resolved:
            lines.append(
                f"- Cleared on {blocker.get('title', 'a task')}: {blocker.get('resolution', '')}"
            )
        lines.append("")

    standings = (summary.get("xp") or {}).get("standings") or []
    if standings:
        lines.append("*Bragging rights*")
        medals = ["🥇", "🥈", "🥉"]
        for index, row in enumerate(standings):
            medal = medals[index] if index < len(medals) else "•"
            lines.append(f"{medal} {row.get('name', 'someone')} - {row.get('amount', 0)} XP")
        lines.append("")

    lines.append(
        f"{counts.get('ideas', 0)} ideas · {counts.get('decisions', 0)} decisions · "
        f"{counts.get('tasks_created', 0)} tasks"
    )
    lines.append(PLAYFUL_FOOTER)
    return "\n".join(lines).strip()
