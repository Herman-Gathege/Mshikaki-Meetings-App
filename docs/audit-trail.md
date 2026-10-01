# Audit trail

The record is the reason Mshikaki exists. The design is argued in
[08-audit-trail.md](08-audit-trail.md); this is how it works in the code.

## What is recorded

Only verbs in the whitelist in `backend/app/domain/activity.py`. An unknown verb
raises, so a typo becomes a failing test rather than an unreadable history entry.
The verbs cover: sessions and their lifecycle, participants and attendance,
agenda, games and scoring, ideas, decisions, tasks, blockers, comments, projects,
membership and access, refused actions, XP and achievements.

**Never recorded:** page views, searches, typing, presence, notification reads,
"user is online". If it is not in the whitelist, it is not in the trail.

## How a record is written

```python
record_activity(
    db,
    team_id=...,
    session_id=...,          # so the meeting view can show it in order
    actor=actor,             # a user, a credited guest, or None for the system
    actor_name=...,
    verb="task.status_changed",
    target_type="task",
    target_id=task.id,
    payload={"title": task.title, "old": previous, "new": status},
)
```

Rules the code depends on:

1. **One transaction.** The change and its activity row commit together, so a
   partial state is impossible.
2. **One write path.** `app/services/activity.py` is the only function that
   inserts into `activity`.
3. **The payload carries the story.** Titles and old and new values, not just
   ids, so history stays readable after a rename or a delete.
4. **The sentence is generated.** `describe(verb, payload)` renders every record
   the same way everywhere.

## What is rendered

`ActivityFeed` in the frontend shows "Mary added the idea "Improve library
search."" because the API sends both the verb and the sentence. Coalescing of
rapid edits is a display concern only; storage keeps every row.

## Immutability

Two layers, because a promise needs more than good intentions:

- The application never updates or deletes an activity row.
- A database trigger rejects `UPDATE` and `DELETE` on `activity` and
  `xp_events`, for every role, including the application's own.

A test creates activity, tries both, and asserts the rows are unchanged.

## Refused actions

`ensure_can` and `require_capability` record `permission.denied` in their own short
transaction, so it survives the rollback of the refused request. Visibility is
admin-only: this is an audit fact, not a scoreboard.

## Reading it

| Surface | What it answers |
|---|---|
| A task, idea, decision or project page | the story of that one thing |
| A session's Activity tab | what happened in that meeting, in order |
| `/activity` | what the team has been doing, filterable by kind |

Every mutating endpoint has a test asserting its activity row, so a service that
forgets to record is a build failure rather than a silent hole.
