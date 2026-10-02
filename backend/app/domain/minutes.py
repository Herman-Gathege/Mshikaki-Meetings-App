"""Meeting minutes: the frozen summary rendered as a printable document.

Rule-based, like the summary it comes from. No language model touches this, so
the minutes for a meeting never change once the meeting is closed.
"""

from __future__ import annotations

from html import escape
from typing import Any

# The one-word outcome of an agenda item, said the way a person would.
OUTCOME_WORDS: dict[str, str] = {
    "accomplished": "done with this",
    "pending": "still pending",
    "assigned": "someone is taking this",
    "none": "nothing decided",
}


def _text(value: Any, fallback: str = "—") -> str:
    if value in (None, "", []):
        return fallback
    return escape(str(value))


def _list(values: list[Any] | None, fallback: str = "None recorded") -> str:
    items = [str(value) for value in (values or []) if value]
    if not items:
        return f"<p class='muted'>{escape(fallback)}</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "<p class='muted'>None recorded</p>"
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_text(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_minutes_html(
    snapshot: dict[str, Any],
    *,
    team_name: str,
    reference: str,
) -> str:
    """A self-contained, printable document. Nine sections, in order."""
    session = snapshot.get("session") or {}
    counts = snapshot.get("counts") or {}
    attendance = snapshot.get("attendance") or {}
    games = snapshot.get("games") or []
    ideas = snapshot.get("ideas") or []
    decisions = snapshot.get("decisions") or []
    tasks = snapshot.get("tasks_created") or []
    blockers = snapshot.get("blockers") or {}
    raised = blockers.get("raised") or []
    resolved = blockers.get("resolved") or []
    agenda = snapshot.get("agenda") or []
    notes = snapshot.get("notes") or []
    generated = snapshot.get("generated_at")

    parts: list[str] = []
    parts.append(
        f"""
<h1>MSHIKAKI MEETING MINUTES</h1>
<h2 class="doc-title">{_text(session.get("title"), "Meeting")}</h2>

<h3>1. Meeting details</h3>
<table>
  <tbody>
    <tr><th>Meeting</th><td>{_text(session.get("title"), "Meeting")}</td></tr>
    <tr><th>Team</th><td>{_text(team_name, "Team")}</td></tr>
    <tr><th>Date</th><td>{_text(session.get("scheduled_at") or session.get("started_at"), "Not recorded")}</td></tr>
    <tr><th>Started</th><td>{_text(session.get("started_at"), "Not recorded")}</td></tr>
    <tr><th>Ended</th><td>{_text(session.get("ended_at"), "Not recorded")}</td></tr>
    <tr><th>Facilitator</th><td>{_text(session.get("facilitator_name"), "Not recorded")}</td></tr>
    <tr><th>Location</th><td>{_text(session.get("location"), "Not recorded")}</td></tr>
  </tbody>
</table>
<p><strong>Present:</strong> {_text(", ".join(str(n) for n in (attendance.get("present") or [])), "None recorded")}</p>
<p><strong>Absent:</strong> {_text(", ".join(str(n) for n in (attendance.get("absent") or [])), "None recorded")}</p>
"""
    )

    parts.append("<h3>2. Agenda</h3>")
    if agenda:
        parts.append("<ol>")
        for item in agenda:
            outcome = item.get("outcome")
            label = OUTCOME_WORDS.get(str(outcome)) if outcome else None
            marker = f" <span class='muted'>({escape(label)})</span>" if label else ""
            parts.append(f"<li>{_text(item.get('title'), 'Item')}{marker}</li>")
        parts.append("</ol>")
    else:
        parts.append("<p class='muted'>No agenda was recorded</p>")

    parts.append("<h3>3. Opening and play</h3>")
    parts.append(
        _table(
            ["Game", "Type", "Questions", "Winner"],
            [
                [
                    game.get("name"),
                    game.get("family"),
                    len(game.get("standings") or [])
                    and f"{len(game.get('standings') or [])} players",
                    game.get("winner"),
                ]
                for game in games
            ],
        )
    )

    parts.append("<h3>4. Ideas raised</h3>")
    parts.append(
        _table(
            ["Idea", "Raised by", "Status", "Under"],
            [
                [
                    idea.get("title"),
                    idea.get("author"),
                    idea.get("status"),
                    idea.get("agenda_title") or "the meeting",
                ]
                for idea in ideas
            ],
        )
    )

    parts.append("<h3>5. Decisions made</h3>")
    if decisions:
        parts.append("<ol>")
        for decision in decisions:
            rationale = (
                f"<p class='muted'>{escape(str(decision.get('rationale')))}</p>"
                if decision.get("rationale")
                else ""
            )
            parts.append(
                f"<li><strong>{_text(decision.get('statement'), 'Decision')}</strong>"
                f"<p class='muted'>Recorded by {_text(decision.get('recorded_by'), 'unknown')}</p>"
                f"{rationale}</li>"
            )
        parts.append("</ol>")
    else:
        parts.append("<p class='muted'>None recorded</p>")

    parts.append("<h3>6. Notes</h3>")
    if notes:
        parts.append("<ul>")
        for note in notes:
            under = note.get("agenda_title")
            suffix = f" <span class='muted'>({escape(str(under))})</span>" if under else ""
            parts.append(f"<li>{escape(str(note.get('body') or ''))}{suffix}</li>")
        parts.append("</ul>")
    else:
        parts.append("<p class='muted'>No notes were kept.</p>")

    parts.append("<h3>7. Action items</h3>")
    parts.append(
        _table(
            ["Action", "Owner", "Due", "Status", "From"],
            [
                [
                    task.get("title"),
                    task.get("owner") or "Unassigned",
                    task.get("due_date"),
                    task.get("status"),
                    task.get("agenda_title") or "the meeting",
                ]
                for task in tasks
            ],
        )
    )

    parts.append("<h3>8. Blockers</h3>")
    if raised:
        parts.append("<p><strong>Raised during the meeting</strong></p>")
        parts.append(
            _table(
                ["Task", "Reason", "Raised by"],
                [[item.get("title"), item.get("reason"), item.get("raised_by")] for item in raised],
            )
        )
    if resolved:
        parts.append("<p><strong>Cleared during the meeting</strong></p>")
        parts.append(
            _table(
                ["Task", "Resolution", "Cleared by"],
                [
                    [item.get("title"), item.get("resolution"), item.get("resolved_by")]
                    for item in resolved
                ],
            )
        )
    if not raised and not resolved:
        parts.append("<p class='muted'>Nothing was blocked.</p>")

    parts.append("<h3>9. Closing summary</h3>")
    parts.append(
        _table(
            ["Item", "Count"],
            [
                ["Agenda items", counts.get("agenda_items", 0)],
                ["Ideas raised", counts.get("ideas", 0)],
                ["Decisions made", counts.get("decisions", 0)],
                ["Actions created", counts.get("tasks_created", 0)],
                ["Actions completed", counts.get("tasks_completed", 0)],
                ["Notes kept", counts.get("notes", 0)],
                ["Games played", counts.get("games", 0)],
                ["Participants", counts.get("participants", 0)],
            ],
        )
    )

    parts.append("<h3>10. Record information</h3>")
    parts.append(
        "<p class='muted'>"
        f"Mshikaki session reference {escape(reference)}. "
        f"Minutes generated from the frozen session record on {_text(generated, 'close')}. "
        "This document is a snapshot: regenerating it is an explicit, recorded action."
        "</p>"
    )

    body = "\n".join(parts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Minutes - {_text(session.get("title"), "Meeting")}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
         color: #12100f; background: #fff; margin: 0 auto; max-width: 820px; padding: 32px 24px 64px;
         line-height: 1.5; }}
  h1 {{ font-size: 20px; letter-spacing: .12em; text-transform: uppercase; color: #b1451f;
        border-bottom: 3px solid #b1451f; padding-bottom: 8px; margin: 0 0 4px; }}
  h2.doc-title {{ font-size: 26px; margin: 12px 0 24px; }}
  h3 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .06em; color: #4a4a48;
        margin: 28px 0 8px; border-bottom: 1px solid #e6e2dd; padding-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0 4px; }}
  th, td {{ text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid #eeeae6;
            font-size: 14px; }}
  thead th {{ background: #f7f5f2; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
  tbody th {{ width: 30%; color: #6b6762; font-weight: 600; }}
  ul, ol {{ margin: 6px 0 6px 20px; padding: 0; }}
  li {{ margin: 4px 0; }}
  .muted {{ color: #6b6762; font-size: 13px; }}
  @media print {{ body {{ padding: 0; max-width: none; }} h3 {{ break-after: avoid; }}
                  table, li {{ break-inside: avoid; }} }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
