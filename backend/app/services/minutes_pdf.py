"""The meeting minutes as a PDF, from the same frozen snapshot as the HTML.

One renderer, one source. The HTML is what a browser shows; this is what a
person prints or attaches to an email. It reads the snapshot and writes pages,
so a meeting summarised twice can never disagree with itself.

Reportlab is used as a library, not a document framework: paragraphs and tables,
no templates and no second content model.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#12100F")
MUTED = colors.HexColor("#6B6762")
EMBER = colors.HexColor("#B1451F")
LINE = colors.HexColor("#E3DED8")

OUTCOME_WORDS = {
    "accomplished": "done with this",
    "pending": "still pending",
    "assigned": "someone is taking this",
    "none": "nothing decided",
}


def _escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MshikakiTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_LEFT,
            textColor=EMBER,
            spaceAfter=2,
        ),
        "heading": ParagraphStyle(
            "MshikakiHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=INK,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "MshikakiBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
        ),
        "muted": ParagraphStyle(
            "MshikakiMuted",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
        ),
    }


def _table(rows: list[list[Any]], headers: list[str]) -> Table:
    data = [[Paragraph(f"<b>{_escape(h)}</b>", _styles()["body"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(_escape(cell) or "—", _styles()["body"]) for cell in row])
    table = Table(data, hAlign="LEFT", colWidths=None)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4EFE9")),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _agenda_line(item: dict[str, Any]) -> str:
    """One agenda line, with the outcome in parentheses when there is one."""
    line = _escape(item.get("title"))
    word = OUTCOME_WORDS.get(str(item.get("outcome")))
    return f"{line} <font color='#6B6762'>({_escape(word)})</font>" if word else line


def _note_line(note: dict[str, Any]) -> str:
    line = _escape(note.get("body"))
    under = note.get("agenda_title")
    return f"{line} <font color='#6B6762'>({_escape(under)})</font>" if under else line


def render_minutes_pdf(snapshot: dict[str, Any], *, team_name: str, reference: str) -> bytes:
    """The printable minutes. Same snapshot, same facts as the HTML."""
    session = snapshot.get("session") or {}
    counts = snapshot.get("counts") or {}
    attendance = snapshot.get("attendance") or {}
    agenda = snapshot.get("agenda") or []
    games = snapshot.get("games") or []
    ideas = snapshot.get("ideas") or []
    decisions = snapshot.get("decisions") or []
    tasks = snapshot.get("tasks_created") or []
    notes = snapshot.get("notes") or []
    blockers = snapshot.get("blockers") or {}

    style = _styles()
    story: list[Any] = []
    story.append(Paragraph("MSHIKAKI MEETING MINUTES", style["title"]))
    story.append(Paragraph(_escape(session.get("title") or "Meeting"), style["heading"]))
    story.append(
        Paragraph(
            f"{_escape(team_name)} · generated {_escape(snapshot.get('generated_at') or '')}",
            style["muted"],
        )
    )
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Meeting details", style["heading"]))
    story.append(
        _table(
            [
                [
                    "Date",
                    session.get("scheduled_at") or session.get("started_at") or "Not recorded",
                ],
                ["Started", session.get("started_at") or "Not recorded"],
                ["Ended", session.get("ended_at") or "Not recorded"],
                ["Facilitator", session.get("facilitator") or "Not recorded"],
                ["Location", session.get("location") or "Not recorded"],
                ["Present", ", ".join(str(n) for n in (attendance.get("present") or [])) or "None"],
                ["Absent", ", ".join(str(n) for n in (attendance.get("absent") or [])) or "None"],
            ],
            ["Item", "Detail"],
        )
    )

    story.append(Paragraph("2. Agenda", style["heading"]))
    if agenda:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_agenda_line(item), style["body"])) for item in agenda],
                bulletType="1",
                leftIndent=14,
            )
        )
    else:
        story.append(Paragraph("No agenda was recorded.", style["muted"]))

    if games:
        story.append(Paragraph("3. Opening and play", style["heading"]))
        story.append(
            _table(
                [[game.get("name"), game.get("winner") or "no winner"] for game in games],
                ["Game", "Winner"],
            )
        )

    story.append(Paragraph("4. Ideas raised", style["heading"]))
    if ideas:
        story.append(
            _table(
                [
                    [
                        idea.get("title"),
                        idea.get("author"),
                        idea.get("status"),
                        idea.get("agenda_title") or "the meeting",
                    ]
                    for idea in ideas
                ],
                ["Idea", "Raised by", "Status", "Under"],
            )
        )
    else:
        story.append(Paragraph("None recorded.", style["muted"]))

    story.append(Paragraph("5. Decisions made", style["heading"]))
    if decisions:
        story.append(
            _table(
                [
                    [
                        decision.get("statement"),
                        decision.get("recorded_by"),
                        decision.get("agenda_title") or "the meeting",
                    ]
                    for decision in decisions
                ],
                ["Decision", "Recorded by", "Under"],
            )
        )
    else:
        story.append(Paragraph("None recorded.", style["muted"]))

    story.append(Paragraph("6. Notes", style["heading"]))
    if notes:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_note_line(note), style["body"])) for note in notes],
                bulletType="bullet",
                leftIndent=14,
            )
        )
    else:
        story.append(Paragraph("No notes were kept.", style["muted"]))

    story.append(Paragraph("7. Action items", style["heading"]))
    if tasks:
        story.append(
            _table(
                [
                    [
                        task.get("title"),
                        task.get("owner") or "Unassigned",
                        task.get("due_date") or "—",
                        task.get("status"),
                        task.get("agenda_title") or "the meeting",
                    ]
                    for task in tasks
                ],
                ["Action", "Owner", "Due", "Status", "From"],
            )
        )
    else:
        story.append(Paragraph("No actions were needed.", style["muted"]))

    raised = blockers.get("raised") or []
    resolved = blockers.get("resolved") or []
    if raised or resolved:
        story.append(Paragraph("8. Blockers", style["heading"]))
        story.append(
            _table(
                [[item.get("title"), item.get("reason"), "raised"] for item in raised]
                + [[item.get("title"), item.get("resolution"), "cleared"] for item in resolved],
                ["Task", "What happened", "When"],
            )
        )

    story.append(Paragraph("9. Closing summary", style["heading"]))
    story.append(
        _table(
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
            ["Item", "Count"],
        )
    )

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f"Mshikaki session reference {_escape(reference)}. "
            "This document is a snapshot of the frozen meeting record.",
            style["muted"],
        )
    )

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Minutes - {session.get('title') or 'Meeting'}",
        author="Mshikaki",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    document.build(story)
    return buffer.getvalue()
