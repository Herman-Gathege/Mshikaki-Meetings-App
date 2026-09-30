# 08 - Audit Trail

## Why this is the real feature

The games get people in the room. The audit trail is why the product exists.

The questions it must answer, without anyone writing minutes:

- What did we decide, and when?
- Who decided it, and who was in the room?
- Why does this task exist?
- Who was supposed to do this, and what changed since?
- What did we talk about in March?

If the answer to any of these requires scrolling WhatsApp, MVP 1 has failed at its
main job, regardless of how fun the trivia was.

## Hard requirements

| # | Requirement |
|---|---|
| 1 | **Automatic.** No user action produces a record. There is no "save note" step |
| 2 | **Complete.** Every create, update, status change, assignment, comment, delete and restore on a tracked entity is recorded |
| 3 | **Attributed.** Every record names an actor: a user, a credited guest, or `system`, plus the actor on whose behalf it happened when relevant |
| 4 | **Immutable.** Records are never updated or deleted by application code |
| 5 | **Timestamped.** UTC in storage, displayed in the team's timezone, with session-local ordering preserved |
| 6 | **Contextual.** Each record carries enough context to be read as a sentence with no lookup: actor, action, subject, and the previous and new value for changes |
| 7 | **Traversable.** Readable per entity, per session, and per team; filterable by actor, verb, entity type and date |
| 8 | **Portable.** A session's record can be exported as human text, because the team will paste it into WhatsApp |
| 9 | **Explainable.** Any score, achievement, or summary can be traced back to the events that caused it |
| 10 | **Bounded in noise.** It records what matters, not views and scrolls |

## What counts as a meaningful event

The discipline is the whitelist. If a verb is not in this table, it does not
produce an activity row.

| Verb | Target | Payload must include | XP eligible | Visible to |
|---|---|---|---|---|
| `session.created` | session | title, scheduled_at | no | team |
| `session.started` | session | participant count | no | team |
| `session.closed` | session | summary id, counts | no | team |
| `session.reopened` | session | reason | no | team |
| `session.participant_joined` | session | participant, role | yes (attendance) | team |
| `game.started` | game_play | game, pack | no | participants |
| `game.finished` | game_play | standings | yes (play, placement) | participants |
| `game.score_adjusted` | game_score | old, new, reason | no | team |
| `idea.created` | idea | title | yes | team |
| `idea.updated` | idea | changed fields, old, new | no | team |
| `idea.status_changed` | idea | old, new, note | yes (accepted only) | team |
| `idea.converted` | idea | target type, target id | no | team |
| `idea.commented` | idea | excerpt | no | team |
| `decision.recorded` | decision | statement | yes | team |
| `decision.superseded` | decision | old id, new id | no | team |
| `task.created` | task | title, owner, origin links | no | team |
| `task.assigned` | task | old owner, new owner | no | team |
| `task.status_changed` | task | old, new, reason | yes (done only) | team |
| `task.due_date_changed` | task | old, new | no | team |
| `task.priority_changed` | task | old, new | no | team |
| `task.reopened` | task | reason | no | team |
| `blocker.raised` | blocker | reason, task | no | team |
| `blocker.resolved` | blocker | resolution, task | yes (Firefighter) | team |
| `comment.created` | any | excerpt | no | team |
| `comment.deleted` | any | excerpt | no | team |
| `project.created` / `updated` / `status_changed` | project | changes | no | team |
| `achievement.awarded` | user or guest | achievement, source | no | team |
| `xp.awarded` / `xp.reversed` | user or guest | amount, reason | no | team |
| `member.joined` / `role_changed` / `removed` | membership | old, new role | no | admin |
| `permission.denied` | any | attempted action | no | admin |

Explicitly **not** recorded: page views, searches, typing into an open form,
notification reads, "user is online", scroll depth. They add noise and create a
surveillance feeling that will get the product killed internally.

## Noise control

A trail nobody can read is not a trail.

- **Coalesce on display, never in storage.** Five edits in two minutes render as
  one expandable line ("Herman edited this task 5 times") while five immutable rows
  sit underneath. Storage stays honest; the UI stays readable.
- **One sentence per record**, generated from verb + payload by a single shared
  formatter, so every screen reads the same way.
- **Session activity is chronological and complete**; team activity is filtered and
  summarised by default.
- **Counts over noise in summaries.** The session summary says "6 ideas captured",
  not six separate lines.

## Data shape

```text
activity(
  id, team_id, session_id,
  actor_type ('user'|'guest'|'system'), actor_id,
  verb,                       -- from the whitelist
  target_type, target_id,     -- the subject of the verb
  payload jsonb,              -- old/new values, titles, excerpts, counts
  occurred_at timestamptz,
  source,                     -- 'web' | 'api' | 'job' | 'import'
  visibility                  -- 'team' | 'participants' | 'admin'
)
```

Design notes:

- `session_id` is denormalised onto the row even when it can be derived, because
  session history is the most common read and joins on every read are waste.
- `payload` holds the human-readable essentials (titles, old and new values), not
  just ids, so history stays readable after an entity is renamed or deleted.
- `visibility` exists for the small number of records that should not be
  team-visible (role changes, permission denials).
- No foreign keys on `target_id`; refs are resolved at read time and rendered as
  "deleted item" when they no longer exist.

## Enforcement

- **Database grants**: the app role has `INSERT` and `SELECT` on `activity`, no
  `UPDATE`, no `DELETE`. Same for `xp_events` and `achievement_awards`.
- **One write path**: a single server-side "record activity" helper is the only
  thing that inserts. Services never insert directly, and no route writes raw SQL
  for it.
- **Repository-level check**: creating or updating a tracked entity through the
  data layer without a corresponding activity write should be a test failure, not a
  code review comment. This is worth a dedicated integration test per entity.
- **Backfill discipline**: if a new event type is added, historical gaps are left
  as gaps. Never fabricate history.

## Editing and deletion semantics

People make mistakes. The trail must survive the correction.

| Action | What happens |
|---|---|
| Edit content | Row updated, `edited_at` set, activity row with old and new values |
| Delete content | `deleted_at` set, activity row containing a snapshot of the deleted content |
| Restore | `deleted_at` cleared, activity row `restored` |
| Hard delete | Only by an admin, only for content that should never have existed (profanity, personal data), and the activity row remains with the snapshot removed |
| Erase a person (right to be forgotten) | `users` row is anonymised, `activity.actor_id` is nulled with a `redacted` flag, and the activity rows survive as attributed to "former member". Deleting the rows would break the team's history, which is a legitimate interest that must be balanced against the request |

Note the tension: an unbreakable audit trail and a right to erasure are in direct
conflict. Resolve it by anonymising the person, not the events, and say so
explicitly in the team-facing privacy note rather than discovering it in a
conversation later.

## The session summary (the skewer)

Generated at session close, stored as a snapshot, regenerable on demand.

Content, in order:

1. Session title, date, duration, facilitator, attendees (and who was absent)
2. Games played, with winner and standings per game
3. Ideas captured (title, author, status), with the full text of accepted ones
4. Decisions recorded (statement, who recorded it)
5. Tasks created (title, owner, due date), plus tasks completed and reopened during
   the session
6. Blockers raised and resolved
7. Parked and rejected ideas, explicitly, so nothing silently vanishes
8. XP awarded in the session and the session standings
9. A link back into the app for every item

Renderings:

- **In-app**: readable page with links.
- **Plain text / WhatsApp**: titles, owners, due dates, decision statements.
  This is the highest-value export in the whole product and should be one tap.
- **Print/PDF**: later, if anyone asks.

Generation is rule-based from the activity trail and domain rows. No LLM: the
summary must be deterministic, free, instant, and impossible to hallucinate.

## Review surface

Three reads of the same data, each with a different job:

| Surface | Job | Default ordering |
|---|---|---|
| Entity activity (task, idea, decision, project, session) | "What is the story of this thing?" | Oldest first, coalesced |
| Session activity | "What happened in this meeting?" | Chronological, complete |
| Team activity | "What has been going on, and who is doing it?" | Newest first, filtered |

## Performance

- The hot queries are `(target_type, target_id)` and `(session_id)`; both are
  indexed per [04](04-data-model.md).
- The team feed is paginated by cursor on `(occurred_at, id)`, never offset.
- The session summary is a snapshot, not a live aggregation, so opening a session
  from two years ago is as cheap as opening yesterday's.
- Expected volume is trivial (tens of thousands of rows over years); the risk is
  an unindexed query, not data size.
