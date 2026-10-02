# The agenda-led meeting

Added on 2 October 2026, after the Phase 6 work. This is the product-flow
addition: the agenda is the backbone of a Mshikaki meeting, and play is an
option rather than a requirement.

The rule that has not changed: **one facilitator drives the room, everybody
follows**, and the meeting is still one session with one record.

## The two journeys

Both start the same way and end in the same minutes. They differ only in how the
room opens.

**Serious meeting**

```
create session  ->  set the agenda  ->  QR join  ->  Start meeting
   ->  Agenda 1  ->  discuss, note, decide, assign  ->  Next agenda
   ->  ...  ->  That's a wrap  ->  summary: HTML / PDF / text
```

**Playful meeting**

```
create session  ->  set the agenda  ->  QR join  ->  Let's play
   ->  game and results  ->  Start meeting  ->  the same agenda walk
   ->  That's a wrap  ->  the same summary
```

There is no separate "serious meeting" entity. The opening choice is the only
difference.

## Opening choice

The first Run Mode screen says **Ready to begin?** and offers two buttons:

- **Let's play** - pick a game and a question pack, play it, then start the meeting.
- **Start meeting** - go straight to the agenda.

`POST /sessions/{id}/meeting/start` is the second option. It puts the room on the
first agenda item and sets the stage to `agenda`. Re-entering the agenda later
(after a game, or by tapping the stage) leaves the room on the item it was on.

## Walking the agenda

The session remembers the item under discussion: `sessions.current_agenda_item_id`.
The facilitator moves it, everybody else polls the session and follows, exactly
like the Run Mode stage.

| Action | Endpoint |
|---|---|
| Enter the meeting at the first item | `POST /sessions/{id}/meeting/start` |
| Finish this item and move on (or wrap at the end) | `POST /sessions/{id}/agenda/next` |
| Jump to a specific item | `POST /sessions/{id}/agenda/{item}/current` |
| Say how the item ended | `POST /sessions/{id}/agenda/{item}/outcome` |

The agenda screen shows **Agenda 2 of 5** with a progress bar, the item title,
and four quiet choices for how it ends:

| Outcome | What it means |
|---|---|
| `accomplished` | Done with this |
| `pending` | Still pending |
| `assigned` | Someone is taking this |
| `none` | Nothing decided |

Nothing is forced. An item that produced no decision and no action is a valid
outcome, and recording `none` is one tap.

## Notes

A note is a line worth keeping, and it is deliberately not an idea, a decision or
a task. "Finance will confirm the figure tomorrow" is a note.

- `POST /sessions/{id}/notes` with `{body, agenda_item_id?}`.
- Anybody in the room may add one (`note.create`); the facilitator may remove one.
- Notes appear under the item they were taken under, and in the minutes.

The notes table is small on purpose: body, author, the meeting, and the item.
No rich text, no attachments, no folders.

## Ideas, decisions and actions under an item

Ideas, decisions and tasks all carry an optional `agenda_item_id`, so the record
can answer "where did this come from?" with the item rather than only the meeting.

```
Meeting -> Agenda item -> Idea -> Decision -> Action
```

In the meeting this stays simple:

- An idea captured while the room is on an item is attached to that item by
  default, and can still be attached to the meeting alone.
- The facilitator records one decision in a sentence, and gives one person one
  action. Both appear beside the item that produced them.
- Actions are not compulsory. One action per item is the norm, not five.

## What the meeting produces

Closing writes the summary from the frozen record, as before, and the minutes
now follow the agenda:

1. Meeting details
2. Agenda, with how each item ended
3. Opening and play, when there was a game
4. Ideas raised, with the item each came from
5. Decisions made, with the item each came from
6. Notes
7. Action items, with owner, due date, status and the item it came from
8. Blockers
9. Closing summary, including agenda items and notes kept
10. Record information

Three downloads come from the same snapshot:

| Format | Endpoint |
|---|---|
| HTML minutes | `GET /sessions/{id}/minutes.html` |
| PDF minutes | `GET /sessions/{id}/summary.pdf` |
| Plain text for WhatsApp | `GET /sessions/{id}/export.txt` |

The PDF is rendered by reportlab from the same snapshot the HTML uses, so the two
can never disagree. It is a library, not a document framework: paragraphs, lists
and tables, A4, printable, no external service.

## What was deliberately not built

No WebSockets (the polling that already drives Run Mode is enough), no second
meeting engine, no agenda-level permissions beyond "the facilitator moves the
room", no note editor, no task explosion from a discussion, no dashboards.

## Verified on 2 October 2026

Against the deployed app at `172.16.1.36:8090`:

- **Flow A, two browsers**: the opening choice offered both paths; the
  facilitator started the meeting and landed on *Agenda 1 of 4*; a joiner on a
  390px phone landed on the same item and was told who was leading; the joiner
  added a note that the room saw; the facilitator recorded a decision, assigned
  one action, and marked the item done; *Next agenda* moved both screens; the
  walk reached the wrap; closing released everybody to the session page; the
  minutes contained the agenda, the note and the action; the PDF downloaded as a
  real `%PDF-` file.
- **Flow B, two browsers**: the opening offered the game, the joiner was pulled
  into it, and after the game the meeting started on the same agenda both
  screens shared, ending in the same minutes and PDF.
- **Backend**: 168 tests, including a serious-meeting journey from create to PDF,
  the playful journey sharing one meeting, the pure agenda rules, and the
  permission rows for notes.

**Regressions around the new walk**, checked against the deployment:

| Check | Result |
|---|---|
| The join code still previews the meeting | 200, with the session title |
| Somebody who scans *after* the agenda has started | lands in Run Mode on the current item (2 of 2) |
| The join is on the trail | `meeting.started`, `agenda.covered`, `session.participant_joined` |
| A participant tries to move the room | 403 |
| The game still pulls the room in from the play opening | joiner reached `/play/{id}` |
| Minutes, text export and PDF after the walk | all three present, PDF is a real `%PDF-` file |

## The three questions, asked of the rendered screens

The brief asks whether a child, a serious participant and a facilitator can each
answer their question without reading documentation. The rendered screens were
inspected at 390px and at projector width:

| Who | Question | What the screen says |
|---|---|---|
| First-time user, on a phone | What are we doing now? | `AGENDA 1 OF 2` over `Q4 project progress` |
| Serious participant | Which item are we on? | the item title, plus "The facilitator is leading this item" |
| Participant, on what they can do | How do I contribute? | `📝 Add a note` and `💡 Add an idea` |
| Facilitator | What do I do next? | "How does this item end?", "Move the room to the next item when this one is done", `Next agenda →` |

No answer needs documentation. What is *not* verified: a person on real hardware
(projector, phone, screen reader). That pass is still worth doing before the team
relies on it.

## A deliberate simplification

An idea captured while the room is on an item is attached to that item
automatically rather than asking "this meeting, or this item?". The backend
accepts either; the screen picks the useful default and keeps "Add idea" a
one-tap action, which is what the brief asked to protect.
