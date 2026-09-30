# 05 - Journeys, Information Architecture and Permissions

## The one journey that matters

Everything else supports this. If a design decision makes this flow longer, it is
wrong.

| # | Step | Who | Where | System does automatically |
|---|---|---|---|---|
| 1 | Create session: title, date, agenda | Facilitator | Web (any device) | Sequence number assigned, participants invited |
| 2 | People join | Participants | Phone or room | Attendance recorded |
| 3 | Launch icebreaker | Facilitator | Shared screen | Play recorded, scores kept, participation XP |
| 4 | Move to discussion | Facilitator | Room, not screen | Agenda item marked covered |
| 5 | Capture ideas | Anyone | Phone, 5 seconds each | Idea created + activity + author credited |
| 6 | Discuss | Room | Room | Status transitions, optional comments |
| 7 | Record decisions | Facilitator or any member | Phone or screen | Decision created and linked to session and idea |
| 8 | Turn into tasks | Facilitator, with the room | Shared screen | Tasks created with origin links |
| 9 | Assign owners | Facilitator | Shared screen | Assignment activity, digest queued |
| 10 | Work happens | Owners | Phone | Status changes, blockers, comments, completion |
| 11 | Session ends | Facilitator | Screen | Summary generated, XP calculated, session closed |
| 12 | Later | Anyone | Anywhere | Walk task -> decision -> idea -> session |

Steps 3-9 happen inside **Run Mode**. Run Mode is not a page among pages; it is a
guided state machine for the room, with one obvious "what now" action and a
persistent capture button.

## Supporting journeys

### A. Plan a session (facilitator, before the meeting)

- Title defaults to "<Team> Session #<n>"; date defaults to the team's usual
  cadence; agenda can be pasted as lines and becomes agenda items.
- Picks an icebreaker from the library, filtered by "5 minutes / any mood /
  6+ people".
- Invites by code or email; team members are added by default.
- One screen, three fields. If it needs more, it is wrong.

### B. Run the meeting

Failure modes to design against: wifi drops mid-game; someone arrives late;
discussion runs long and the game gets skipped; two people capture at once; the
facilitator's laptop dies. Every step must be skippable, resumable, and readable
from a phone at the back of the room.

### C. Capture an idea mid-discussion (any member)

Two taps: type a sentence, save. No category, no status, no assignee. The app may
suggest tags later; it must never demand them. Success means the person never lost
their train of thought.

### D. Decide and assign (facilitator, in the room)

From the session screen: pick an idea -> "Record decision" -> statement
pre-filled from the idea and editable -> save. Then "Create task from decision" ->
title, owner, due date -> save. Two objects, four fields, both linked.

### E. Between meetings (owner and lead)

- Owner: "My work" groups owned tasks as Overdue / This week / Later / Blocked /
  Recently done. One tap to change status. Marking blocked asks one question:
  "What is stopping this?"
- Lead: "Work" shows the team's tasks by status, blocked first. Every blocker has
  an owner question: who is unblocking this?

### F. Traceability (anyone, weeks later)

From a task, "Why does this exist?" walks Task -> Decision -> Idea -> Session.
From a session, "What came out of this?" lists ideas, decisions, tasks and games.
Both directions must work; a one-way link is a dead end.

### G. A late joiner or new member

Joins by invite code, gets a name, appears in the session. They can play, capture
ideas and comment immediately. They cannot change another person's content, close
a session, or edit XP rules.

### H. An absent colleague

Reads the session summary or the exported text. No training, no login for the
export.

## Information architecture

Seven destinations, no nesting deeper than one level below them.

```text
Today ................... next session, my tasks, blockers, recent activity, leaderboard strip
Sessions
  - Session
      - Run Mode (active only)
      - Overview / Summary
      - Agenda
      - Ideas
      - Decisions
      - Tasks
      - Play
      - Activity
Work
  - My tasks
  - All tasks (list | board)
  - Project
      - Tasks
      - Decisions
      - Ideas
      - Activity
Ideas .................... all ideas, filter by status/tag/session
Play ..................... game library, launch a game, past results
Leaderboard .............. season standings, session results, achievements, serious metrics
Activity ................. team-wide trail, filters: person, type, entity, date
Team ..................... members, roles, invites, XP rules, game content, organisation
```

Rules:

- **Max five primary nav items on mobile**: Sessions, Work, Ideas, Play,
  Leaderboard. Today is the logo/home target; Activity and Team live under Today
  and the profile menu. All seven appear in the desktop sidebar.
- No screen is more than two taps from Today.
- Every entity page ends with an Activity section, rendered by one shared
  component.
- Serious metrics sit on the Leaderboard page but are visually separated and
  explicitly unscored, per [07](07-leaderboard-xp.md).

## Screen inventory

| Screen | Priority | Notes |
|---|---|---|
| Today / dashboard | P0 | Empty-state quality decides first impressions |
| Session list | P0 | Includes "next session" and quick create |
| Session detail (tabs) | P0 | The hub |
| **Run Mode** | P0 | The product. Build first, polish hardest |
| Session summary + text export | P0 | The artefact people will actually share |
| Idea quick capture sheet | P0 | Must work from one thumb |
| Idea detail | P0 | Comments, status, promote actions |
| Decision create / detail | P0 | Pre-fill from idea |
| Task create / detail | P0 | Owner, due date, status, links |
| My tasks | P0 | The retention screen between meetings |
| Global activity | P1 | Filters matter more than the feed |
| Search | P1 | Ideas, decisions, tasks. Not comments, not activity |
| Task board | P1 | One board, no configuration |
| Project list / detail | P1 | Flat |
| Game library | P1 | Browse and filter |
| Game play (host console + display) | P1 | Two modes, one engine |
| Game results | P1 | Recorded per session |
| Leaderboard | P1 | Season and session tabs |
| Achievements | P2 | Definitions plus awards |
| Team settings, members, invites | P0 | Needed on day one |
| XP rules admin | P2 | Seeded-only in 1.0 is acceptable |
| Game content admin | P2 | JSON seed in 1.0; UI later |
| Onboarding / empty states | P0 | A brand new team must have a good first ten minutes |

## Roles and permissions

Four team roles plus one session-scoped identity. Resist a fifth role until a real
need appears.

| Role | Meaning |
|---|---|
| `owner` | Created the team. Organisation-level powers plus everything admin has |
| `admin` | Manages members, roles, XP rules, game content, projects |
| `facilitator` | Runs sessions. Elevated powers *inside sessions they facilitate*, not team-wide |
| `member` | Normal participant: capture, comment, own tasks, play |
| `guest` | Session-scoped. Participates without an account. Not a team role |

### Capability matrix

| Capability | owner | admin | facilitator | member | guest |
|---|---|---|---|---|---|
| View team sessions, ideas, decisions, tasks | Y | Y | Y | Y | session only |
| Create a session | Y | Y | Y | Y | N |
| Start / close a session | Y | Y | own sessions | own sessions | N |
| Add or remove participants, credit guests | Y | Y | own sessions | N | N |
| Create idea / decision / task | Y | Y | Y | Y | idea only, session-scoped |
| Edit any idea / decision / task | Y | Y | own sessions only | N | N |
| Edit own content | Y | Y | Y | Y | within session window |
| Delete any content | Y | Y | N | N | N |
| Assign tasks to members | Y | Y | Y | self only | N |
| Assign tasks to guests | own only | Y | Y | N | N |
| Change task status | Y | Y | Y | own or co-owned only | N |
| Comment | Y | Y | Y | Y | session items only |
| Launch a game in a session | Y | Y | Y | N | N |
| Submit or adjust scores | Y | Y | own sessions, audited | N | N |
| Manage game content, XP rules, achievements | Y | Y | N | N | N |
| View serious metrics | Y | Y | Y | Y | N |
| View team-wide audit trail | Y | Y | Y | Y | session only |
| Manage members and roles | Y | Y | N | N | N |
| Organisation settings, delete team | Y | N | N | N | N |

### Permission principles

1. **Authorship beats hierarchy for content.** A member can always edit their own
   idea; an admin cannot silently rewrite it, because the audit trail would
   misrepresent history. Admins edit with attribution instead.
2. **Facilitator power is scoped to the session, not the team.** It expires when
   the session closes.
3. **Guests are constrained by scope, not by role juggling.** Session-scoped,
   time-bounded, idea capture and session comments only.
4. **Permission denials are logged.** Failed attempts are part of the record.
5. **Nothing is hard-deleted by a normal user.** The worst case is a soft delete
   plus an audit entry.

## Mobile-first rules

- Design at 360x640 first. Today and Run Mode must be fully usable there.
- Primary actions sit at the bottom, fixed, one per screen, thumb-reachable.
- No horizontally scrolling tables; lists become cards below 640px.
- Touch targets at least 44x44 px. No hover-only affordances.
- Run Mode is the deliberate exception: optimised for a shared screen - large
  type, high contrast, readable from three metres, keyboard shortcuts for a host
  on a laptop - while still degrading to a usable phone layout.
