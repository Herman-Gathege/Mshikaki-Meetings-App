# 07 - Leaderboard and XP

## Purpose and guardrail

The leaderboard exists to make the fun layer slightly addictive and to give the
team a shared joke. It is a cultural feature.

It is **not** a performance system, and three rules keep it that way:

1. **The disclaimer is visible, permanently, in the UI.** "For fun. Not a
   performance measure." A one-line caption, always on the leaderboard.
2. **Serious metrics live somewhere else and are never scored.** Tasks completed,
   blockers open, cycle time: displayed as plain numbers on a separate, unscored
   view. Nobody is ranked by them in the fun layer.
3. **Anyone can opt out, privately.** `users.leaderboard_opt_out`. Opted-out people
   still receive XP and achievements; they simply do not appear in standings, and
   nobody is told who opted out.

## XP as a ledger

XP is never a mutable number on a user row. It is an append-only ledger.

```text
xp_event: (user|guest, amount, reason_key, source_type, source_id, season, awarded_by, occurred_at)
score = sum(amount) filtered by team and season
```

Consequences worth designing for:

- The leaderboard is a query. Rebalances and corrections are new events with
  negative amounts and a reason, not edits.
- `idempotency_key` makes awarding safe to retry, so a job cannot double-award.
- Achievements are evaluated against the ledger and domain state, not against
  counters.
- Any award can be reversed by an admin, with an audit entry explaining why.

## XP sources

Starting values are deliberately small and tunable via `xp_rules`. Caps matter
more than values.

| Source | Rough value | Caps | Notes |
|---|---|---|---|
| Attend a session | small | 1 per session | Attendance is a real contribution |
| Play a game | small | 3 per session | Participation, not winning |
| Win / place in a game | medium | 1 award per play | 1st > 2nd > 3rd, or top-3 only |
| Submit an idea | small | 3 per day | Caps stop idea-spam from winning |
| Idea accepted by the team | medium | none per day, but bounded by reality | The strongest signal that the output mattered |
| Record a decision | medium | facilitator weight 0.5 | See "facilitator bias" below |
| Comment / contribute | none | - | Not measurable without rewarding spam. Explicitly zero |
| Task completed | medium, weighted by priority | e.g. 5 per week | Only counts once, and only the owner |
| Task reopened | small negative or zero | - | Optional; avoid shaming. Prefer zero |
| Raise a blocker | zero | - | Raising blockers early is good behaviour but trivially farmable |
| **Resolve a blocker** | high ("Firefighter") | none needed, rare by nature | Must be resolved and the task must move forward afterwards |
| Complete a "first" (first task, first idea) | small | one-off | Onboarding nudge, marked as one-off |
| Early bird (first to join a session) | tiny | 1 per session | Pure fun |

### Facilitator bias

Facilitators create sessions, record decisions, and assign tasks, so an uncapped
model makes the facilitator win every season. Mitigations:

- Structural actions are weighted at 0.5 or zero for the facilitator.
- Award XP to the *actor* of the substantive event: if the team accepts an idea,
  the idea's author scores, not whoever pressed the button.
- Achievement criteria must reference domain facts, not button presses.

### Anti-gaming rules

- **Caps per day, per session, and per week** on everything repeatable.
- **Diminishing returns**: the 4th idea in a day is worth less than the 1st.
- **Evidence links required**: task XP requires a task with an owner and a
  completion event; blocker XP requires a resolved blocker and a subsequent status
  change. Nothing is awarded for a bare click.
- **Self-dealing limits**: a person cannot approve their own idea to earn the
  acceptance XP in a single-person team; a second distinct participant must be
  involved in the decision.
- **Retroactive cleanup**: an admin can reverse any award; reversals are audited
  and visible.
- **Never award XP for logins, visits, edits, or creating sessions.**

## Achievements

Definitions are data (`achievements.criteria`), evaluated after relevant events,
and awarded with a source reference so every award is explainable.

| Achievement | Criteria |
|---|---|
| Meeting Monster | Attended N sessions in a row (never misses) |
| Idea Machine | Authored N ideas whose status is not `rejected` |
| Deadline Destroyer | Completed N tasks on or before their due date |
| Project Oracle | N of your ideas reached `accepted` |
| Firefighter | Resolved N blockers where the task subsequently progressed |
| Trivia Champion | Most game wins in a season |
| Quiz Master | Ran N game plays as host |
| Mshikaki Legend | Top-3 season finish in X seasons, or a combined threshold |
| Early Bird | First to join a session, N times |
| Comeback King/Queen | Task reopened and completed within the same week, N times |

Achievements should be rare enough to be worth bragging about: if everyone has
all of them by week two, they are decoration. Start with perhaps 8-12, most of them
season-scoped, and add more only when the team asks.

## Leaderboard views

| View | Default? | Notes |
|---|---|---|
| This session | yes, at session close | The moment of maximum fun: right after the meeting |
| This season | yes, main tab | e.g. a quarter. Keeps newcomers in the game and stops all-time domination |
| All time | secondary | Mostly for legacy bragging rights, low prominence |
| Per achievement | secondary | Who has what |
| Serious metrics (unscored) | separate panel | Plain counts, explicitly not a ranking |

Seasonality is a deliberate design choice: an all-time board set in month one
demotivates everyone who joins later, and there is no way to fix that afterwards.

## Privacy and social safety

- Opt out of standings, keep achievements, no explanation required.
- Never show "lowest score", "least tasks", or a bottom-of-the-table list.
- Never notify someone publicly that they lost XP or had an award revoked; show it
  in their own profile, and in the audit trail where anyone checking can see it
  neutrally.
- Guests can appear in a session's game standings but do not appear in seasonal
  standings unless they claim a profile.
- The digest email, if it shows the leaderboard, must not show anyone's task
  status to the whole team.

## What the leaderboard must not do

- Must not be the only reason to open the app. Retention comes from "what do I
  need to do", not from points.
- Must not be shown to managers as a productivity report. If the team's lead asks
  for that, the answer is the unscored metrics view.
- Must not reward volume over judgement. Ten trivial tasks beat one important
  project in a naive points model; caps and priority weighting blunt this rather
  than solve it, and that is an acceptable MVP 1 trade.
