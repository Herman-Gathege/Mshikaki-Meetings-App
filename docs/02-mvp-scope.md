# 02 - MVP 1 Scope

MVP 1 contains exactly seven concept areas. Nothing else. This file is the
contract: if something is not listed as in-scope here, it does not get built in
MVP 1, however cheap it looks.

## In scope

### 1. Sessions

A Session is a meeting. It is the app's primary unit and its memory.

- Fields: title, date/time, location or "online", facilitator, participants,
  agenda items, status, session summary.
- Status: `planned` -> `active` -> `completed`. (Plus `cancelled`; see
  [09](09-risks-and-open-questions.md), open question 12.)
- Participants include real users **and** guests who have no account.
- **Session Run Mode**: a guided, step-by-step view for the facilitator that walks
  the room through Play -> Capture -> Decide -> Assign -> Close. This is the
  centrepiece of MVP 1, not a nice-to-have.
- **Session summary**: generated from the activity trail when the session closes.
  Readable, exportable, shareable as plain text.

### 2. Games / icebreakers

- A game library of icebreakers, filterable by mood, time available, group size and
  energy level.
- **Two playable formats in MVP 1**: (a) prompt-card decks, played by the room with
  no scoring required; (b) host-paced quiz sets on one shared screen, scored by the
  host.
- Results are recorded against the session (who played, who won, how long).
- A content pack ships with MVP 1 so the app is never empty on day one.
- Deliberately **not** per-phone realtime play in 1.0. See [06](06-games.md).

### 3. Ideas

- Capture: title only is enough; description and tags optional and editable later.
- Fields: title, description, creator, originating session, tags, status, links.
- Status: `new` -> `discussing` -> `accepted` | `parked` | `rejected` |
  `converted`.
- Comments on an idea (one thread, no nesting).
- Ideas get promoted: idea -> decision, idea -> task, idea -> project.

### 4. Decisions

- A decision is a recorded agreement, not a workflow item. No approval states in
  MVP 1.
- Fields: statement, rationale (optional), recorded by, when, originating session,
  links to idea / project / task.
- Decisions can be superseded by a later decision, with a link both ways.
- Searchable, and always visible in the session they came from.

### 5. Tasks / actions

- Fields: title, description, owner, collaborators, status, priority, due date,
  project, originating session, originating idea/decision, comments.
- Status: `backlog` -> `in_progress` -> `done`, plus `blocked` as a state reachable
  from and returning to `in_progress`. Plus `cancelled`.
- Priority: `low` / `normal` / `high` / `urgent`. Four levels, no numeric weights.
- **Blockers are a first-class lightweight entity** (reason, opened by, resolved
  by, resolved at), not just a status flag. This is required by the "Firefighter"
  achievement and by the session summary. See [03](03-domain-model.md).
- Two views: a flat list (default, mobile-first) and a simple board by status.
  No swimlanes, no WIP limits, no burndown.

### 6. Projects

- A Project groups tasks that outlive a single session.
- Fields: name, description, status (`active` / `paused` / `done`), owner, tasks.
- Deliberately flat: **Project -> Task**, with labels for everything else. No
  Group, no sub-project, no milestone.

### 7. Activity / audit trail + leaderboard

- Every meaningful mutation writes an append-only activity record: who, what,
  when, on what, and what changed.
- Two views of the same data: session activity (chronological within a meeting)
  and team activity (filterable by person, entity, type, date).
- Every entity has an activity section, and every entity that originated
  elsewhere carries back-links ("why does this exist?").
- Leaderboard: XP events, achievements, seasonal standings, per-session results.
- **Serious metrics are a separate, unscored view**: tasks completed, blockers
  opened vs resolved, tasks by owner. Never merged into the leaderboard.

## Out of scope for MVP 1 (explicitly deferred)

| Deferred | Why not now | Revisit when |
|---|---|---|
| Per-phone realtime game play | Costs roughly as much as everything else in MVP 1; the model already supports adding it | A second game engine is approved, or sessions prove game-driven |
| Chat / direct messaging | Conversation lives where people already are; building a worse WhatsApp is a trap | Never, probably; maybe threaded comments on tasks only |
| Calendar sync (Google/Outlook) | Two-way sync is a permanent maintenance tax | After sessions are used consistently |
| File attachments | Storage, permissions, virus scanning, quota | A task genuinely needs a document to be done |
| AI assistants / auto-summary by LLM | Rule-based summary is sufficient and free; AI adds cost, latency and unpredictability | After the structured record is trusted |
| Notifications beyond one daily digest | Scope discipline, and email is one integration, not five | After the digest proves insufficient |
| Native mobile apps | The web app must work on phones anyway; a native shell adds release overhead | Push notifications or offline demand it |
| Offline-first sync | Conflict resolution is a large, subtle build | Field teams with genuinely no connectivity |
| QR-code session joining | Nice, cheap, but not needed for a room of colleagues | First guest-heavy or public session |
| External participants / public signup | Identity and abuse handling | Team-vs-team or org-wide sessions |
| Team-vs-team competitions | Needs multi-team scoring and match management | After single-team play is stable |
| Custom workflows, custom fields, custom statuses | The fastest route to becoming Jira | Probably never |
| Org-wide reporting, dashboards, exports beyond summary | Nobody has asked the question yet | A manager asks a question the app cannot answer |
| SSO / SAML | Enterprise table stakes, not small-team table stakes | A second organisation, or an IT policy |
| Integrations (Slack, Jira, GitHub) | Each is a maintenance commitment | A specific workflow is proven and painful |
| Voting / ranking on ideas | Cheap to add, but introduces a second power structure next to the facilitator | Ideas outnumber discussion time regularly |
| Blockers as a separate board | Blockers already surface via task state and activity | Blockers become a recurring coordination problem |
| Recurring session series | Nice for auto-numbering "Session #12"; not load-bearing | Teams ask for it twice |
| Chat-style live reactions during play | Fun, but part of the deferred realtime engine | With per-phone play |

## Scope budget

A rough sense of where effort goes, to protect the loop from being starved by the
fun layer:

| Area | Share of build effort |
|---|---|
| Foundation (auth, teams, roles, audit spine, design system) | ~25% |
| Session + Run Mode + summary | ~25% |
| Work layer (projects, tasks, blockers, views) | ~20% |
| Play layer (one engine, library, scoring, XP, leaderboard) | ~20% |
| Content, seeding, polish, hardening | ~10% |

If the play layer starts exceeding its share, the correct move is to cut game
types, not to extend the timeline.

## Definition of done for MVP 1

1. A facilitator can plan a session, invite the team, and run it live in Run Mode.
2. Guests can participate in a game and be credited, with no account.
3. During the session, ideas, decisions and tasks can be created in under five
   seconds each, on a phone, from the Run Mode screen.
4. Every task has an owner, a status, and a visible origin.
5. Closing a session produces a summary that is accurate without human editing and
   can be pasted into WhatsApp as plain text.
6. Every one of those actions appears in the audit trail, attributed and
   timestamped, with no manual entry anywhere.
7. A person joining six weeks later can walk Task -> Decision -> Idea -> Session
   and understand why the work exists.
8. The leaderboard exists, is fun, is capped against gaming, and can be opted out
   of per person.
9. It works on a phone on a slow connection, and on a shared screen in a room.
10. Nobody has had to be trained.
