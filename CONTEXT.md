# Mshikaki - domain vocabulary

One place for the words. If code and this file disagree, one of them is a bug.

## The loop

**Session** - a meeting. The primary unit of the product. Has a facilitator,
participants, an agenda, and it closes. `planned -> active -> paused -> completed`,
plus `cancelled`. Only one session per team may be `active`.
Not to be confused with **auth session** (a login).

**Run Mode** - the guided, screen-first view a facilitator drives during a
meeting. It opens with a choice (Let's play, or Start meeting) and then walks the
**agenda**: the facilitator moves the room from one item to the next, and
everybody follows. `capture`, `decide` and `assign` are the older per-topic
screens; they still render so a meeting sitting on one is never stranded, but the
agenda carries the work now.

**Agenda item** - one topic in the numbered list for a meeting. The session
remembers which one is current (`current_agenda_item_id`), and each item records
how it ended: `accomplished`, `pending`, `assigned`, or `none` (nothing decided).

**Note** - one line of meeting scratchpad, worth keeping but not an idea, a
decision or a task ("finance will confirm tomorrow"). Belongs to the meeting and,
when the room is on one, to the agenda item under discussion. Anybody in the room
may add one.

**Idea** - something someone proposes. `new -> discussing -> accepted | parked |
rejected`, then `converted` when it becomes work. Ideas do not have to become work.

**Decision** - a recorded agreement. No approval workflow. Can be superseded by a
later decision. May exist without an idea or a session (with a stated reason).

**Task** - the actionable unit. `backlog -> in_progress -> blocked -> done`, plus
`cancelled`. Exactly one owner. Links to the session, idea and decision it came
from; those links are permanent.

**Blocker** - what is stopping a task. A first-class record with a raiser, a
reason, a resolver and a resolution, not just a status flag.

**Project** - a container for work that outlives meetings. Flat: project -> task,
with labels for everything else. No groups, no sub-projects.

**Guest** - a session participant without an account. Can play, capture ideas and
be credited. Cannot log in until they claim a profile.

**Skewer** - the metaphor for traceability: separate pieces threaded onto one
stick. The session summary is the skewer of a meeting.

## The record

**Activity** - the append-only audit trail. Who did what, when, to what, and what
changed. Written automatically; never written by a user.

**Verb** - the activity type, from a fixed whitelist (`task.status_changed`,
`idea.created`, ...). Unknown verbs raise.

**Payload** - the human-readable detail on an activity record: titles, excerpts,
old and new values. Enough to read the history after a rename or a delete.

**Coalescing** - grouping rapid edits into one visible line **for display only**.
Storage keeps every row.

**Frozen summary** - the session snapshot generated at close. Regeneration creates
a new snapshot and marks the old one superseded; it never overwrites.

## The fun layer

**Game family** - one of `prompt_deck` (cards, no right answer), `host_quiz` (the
host paces questions and confirms answers), `host_scored` (a human judges).
Timers, teams and rounds are modifiers, not families.

**Content pack** - a themed set of questions or prompts, as JSON in `content/`,
with a declared license and attribution. Imported by idempotent seeding; never
hard-coded in the frontend.

**Game play** - one instance of a game inside a session, with its host, pack and
scores. `pending -> running -> finished`, or `abandoned`.

**XP event** - one append-only award. A person's score is the sum of their events
for a team and season, never a stored counter.

**Season** - a leaderboard window, e.g. a quarter. Keeps newcomers competitive and
stops all-time domination.

**Achievement** - a named bragging right with defined criteria, awarded from
domain facts and auditable.

## Roles

**owner** - created the team; organisation-level powers.
**admin** - manages members, roles, content and XP rules.
**facilitator** - runs sessions; elevated powers apply only inside sessions they
facilitate, and expire at close.
**member** - normal participant: capture, comment, own tasks, play.
**guest** - session-scoped, no account.

## Statuses in one place

| Entity | Values |
|---|---|
| Session | `planned`, `active`, `paused`, `completed`, `cancelled` |
| Idea | `new`, `discussing`, `accepted`, `parked`, `rejected`, `converted` |
| Task | `backlog`, `in_progress`, `blocked`, `done`, `cancelled` |
| Task priority | `low`, `normal`, `high`, `urgent` |
| Project | `active`, `paused`, `done` |
| Game play | `pending`, `running`, `finished`, `abandoned` |
| Season | `upcoming`, `active`, `closed` |
