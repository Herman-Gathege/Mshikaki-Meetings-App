# 09 - Risks, Contradictions and Open Questions

This is the document to argue with. Read it before the others if you only read
one thing.

## Part 1: Places where the concept is unclear, contradictory, or expensive

Fourteen items. Each one has a severity, the reasoning, and a recommended
resolution that is already reflected in the rest of this package.

### 1. Games are the most expensive thing here, and the brief treats them as a checklist

**Severity: high.** The brief lists roughly twenty game types and says "the system
should eventually support a growing game library". Taken literally, that is a
realtime multiplayer product with a content business attached. It is plausibly
more work than everything else in MVP 1 combined, and it is the part least
connected to the serious purpose.

**Recommendation:** one engine, three families, two playable formats, no
per-phone realtime in 1.0. Ship a rich sealed content pack so the library feels
real on day one, and expand families later without touching the schema.

### 2. `Project -> Group -> Task` adds a level nobody asked for

**Severity: medium.** A third nesting level taxes every mobile screen, every
filter, and every permission check, and it usually turns out to be a label wearing
a costume. It also creates a naming argument ("is this a group or a project?") in
the first team meeting.

**Recommendation:** `Project -> Task` plus free-form labels. If groups are
genuinely needed, promote to an entity in MVP 1.5 when there is a real example and
a real complaint. Cost of deferring is low; the cost of adding it now is paid on
every mobile screen for as long as it remains unused.

### 3. A session cannot contain the work it creates

**Severity: medium-high.** The brief describes a session as containing "tasks/actions
created". But work outlives meetings: a task created in Session #12 is still open
in Session #18, and belongs to a project. If the model makes tasks children of
sessions, every query becomes awkward and moving work between sessions becomes a
manual chore.

**Recommendation:** a task links to its **originating** session and optionally to a
project, and belongs structurally to neither. The session is the source, the
project is the home. This single distinction is what makes traceability work.

### 4. "Not every idea becomes a task" is stated, but the flow implies it usually does

**Severity: medium.** The journey ends with assign-and-do, and the leaderboard
rewards completion, so every incentive pushes toward "everything becomes a task".
That produces a task cemetery within a month and makes the record useless.

**Recommendation:** make the non-action outcomes first-class and visible. Parked,
rejected and accepted-but-not-scoped are normal, respectable endings, shown in the
session summary. Do not add XP for task creation, only for completion, and count
"parked" as a healthy outcome in the summary wording.

### 5. Decision inflation

**Severity: medium.** If recording a decision is a rewarded, easy action, teams
will record trivia ("we agreed to start on time") until the decision list is
noise, and the leaderboard will reward whoever holds the pen.

**Recommendation:** decisions are recorded only when they have a consequence:
a link to a task, a project, or an explicit "this changes what we do" flag. Keep
the facilitator weight at 0.5 in XP. Accept some inflation; the cost of a
too-thorough record is much lower than a wrong one.

### 6. The leaderboard is one sentence away from becoming performance management

**Severity: high.** The brief is clear that it should be fun, and the moment it
exists, someone will screenshot it and use it in a review, or someone will feel
watched. This is the feature most likely to be quietly hated.

**Recommendation:** permanent on-screen disclaimer, per-person opt-out, caps
against farming, no negative rankings, no XP for volume alone, and a strictly
separate unscored metrics panel. Additionally: the leaderboard should never be the
default landing tab.

### 7. "No notifications" is a coherent scope decision and a fatal product decision

**Severity: high.** An audit trail nobody opens is a filing cabinet. Tasks assigned
in a meeting with no reminder two days later will be forgotten, and the app will be
blamed for the forgetfulness. But notifications are also where scope explodes.

**Recommendation:** exactly one notification in MVP 1 - a short daily digest by
email (my tasks due or overdue, blockers I can help with, yesterday's activity
summary). No push, no per-event email, no preferences screen beyond on/off. This
is the one place where the brief's "no notifications" rule should be broken
deliberately, and it should be recorded as an exception rather than a drift.

### 8. "Mobile-friendly" and "one big screen in a room" are different products

**Severity: medium.** Games and shared review want a projector layout; capture
wants a thumb. Trying to make one screen serve both produces a compromise that is
mediocre at both.

**Recommendation:** two explicit layout modes. Run Mode and game display are
screen-first (big type, keyboard shortcuts, readable from three metres). Capture,
My Work and everything between meetings is mobile-first. Both must be usable at
360px, but they are optimised differently on purpose.

### 9. Realtime is implied everywhere and required nowhere

**Severity: medium.** A meeting app naturally suggests "everybody sees it live".
Building that in MVP 1 means websockets, reconnection, presence, conflict
resolution and an order of magnitude more testing.

**Recommendation:** no realtime in MVP 1. Run Mode refreshes on a short poll while
active, appends optimistically, and reconciles. Set expectations in the UI:
refresh, not magic. Revisit only if per-phone play is approved.

### 10. An automatic record of everything can feel like surveillance

**Severity: medium-high.** "Who did what and when" is exactly the phrasing of a
disciplinary file. In a real team, someone will notice.

**Recommendation:** write a one-paragraph team charter for the record: what is
recorded, what is not (no views, no reading, no presence, no typing), who can see
it, and the promise that it is not used for evaluation. Display it on the
onboarding screen, not buried in settings. Deny internal politics the material it
needs.

### 11. The name is playful; the record is not

**Severity: low-medium.** A playful product risks being taken less seriously for
the serious half, and the skewer metaphor will be applied to everything.

**Recommendation:** keep the identity playful and the data sober. The skewer
metaphor is genuinely good for traceability, so use it - but only for the summary
and the trail, never for names of statuses (`backlog`, not "raw"; `done`, not
"grilled").

### 12. Session status set was underspecified

**Severity: low.** The brief says planned / active / completed. Real meetings also
pause, get cancelled, and get reopened the next morning.

**Recommendation:** `planned`, `active`, `paused`, `completed`, `cancelled`, with
one active session per team and an audited reopen. Cheap to model now, painful to
bolt on after a year of data.

### 13. "Don't hard-code KBC or ICT" has a real cost now

**Severity: medium.** Multi-tenancy - organisation, team, membership, scoped
queries, scoped permissions - costs perhaps 10-15% of the foundation effort, and
buys nothing today. Retrofitting it later means touching every table and every
query.

**Recommendation:** keep the table structure general (org -> team -> membership)
and every row team-scoped from the first migration, but build **no** multi-team UI.
One team, one organisation, auto-created at setup. The structure is general; the
product is not yet.

### 14. Guest participants conflict with an attribution-based audit trail

**Severity: low.** If a guest has no account and later claims one, history must be
reattributed without rewriting it.

**Recommendation:** `guests.linked_user_id`, and reattribution is an audited event
("Anne's guest profile was linked to Anne"), while the original activity rows keep
their original actor and gain the link. Never rewrite history in place.

## Part 2: UX risks

| Risk | Why it happens | Mitigation |
|---|---|---|
| The facilitator becomes a laptop operator | Run Mode is interesting, the room is not on the screen | Screen-first Run Mode with one action per step, keyboard shortcuts, and a phone-sized control strip |
| Death by tabs | Every entity wants its own page | Session detail has tabs; everything else is a page with sections and one Activity block |
| Empty first session | Content and examples do not exist yet | Rich seed content, demo-friendly scoring defaults, and a "sample session" that can be deleted |
| Capture friction | Forms with required fields | Title-only creation; every other field optional and editable later; one shared quick-capture sheet reachable from anywhere |
| Audit noise | Everything is logged, so nothing is read | Verb whitelist, display coalescing, counts in summaries, filtered defaults |
| WhatsApp remains the real record | People already live there | One-tap plain-text summary export, designed for pasting, plus the digest email |
| Nobody returns between meetings | Nothing pulls them back | My Work on the Today screen plus the daily digest; not streaks, not badges |
| Games get skipped under time pressure | Meetings overrun | Games are 5-10 minutes by design, skippable, and recorded as skipped rather than silently dropped |
| Leaderboard resentment | Comparison becomes evaluation | Disclaimer, opt-out, caps, no bottom-of-table, separate unscored metrics |
| Guest friction in the room | Account creation mid-meeting | Guests join with a name only; no email required; claimable later |
| Two people capture at once on a shared screen | One host, many contributors | Personal capture always works on a phone, regardless of what the shared screen is doing |

## Part 3: Technical risks

| Risk | Impact | Mitigation |
|---|---|---|
| Overbuilding realtime | Weeks lost, fragile sessions | Explicitly out of scope; polling in Run Mode only |
| Ad-hoc activity logging | The audit trail silently has holes | DB grants preventing update/delete, single write helper, per-entity integration test that asserts an activity row |
| Tenancy leaks | Serious and embarrassing; blocks external teams later | `team_id` on every domain row from the first migration, mandatory scope in the data layer, a test that asserts cross-team reads fail |
| Unreadable history after renames | Traceability degrades over time | Store human-readable titles and values in the activity payload, not only IDs |
| Schema churn in the first month | Migrations on live data, or lost work | Lock the core entity model before Phase 2, keep JSONB for genuinely flexible fields only, and treat migrations as reversible |
| Bad or missing connectivity in the room | The whole meeting stalls | Host-side content preload, local scoring during play, optimistic writes, retries, no hard dependency on the network for the fun layer |
| Low-end Android + iOS Safari quirks | Layout and audio failures exactly when the team watches | Test on a real 360px Android and a real iPhone, not only a devtools emulator. Audio autoplay in particular will bite; do not depend on it |
| Content licensing | Legal exposure, packs pulled late | License and attribution columns, no lyrics or film quotes, original content preferred, a review step before a pack ships |
| Speed-based scoring unfairness on shared wifi | Trust in the leaderboard collapses | Speed bonuses small or off; host override available; position over points |
| Timer and timezone bugs | Wrong session times, confusing history | UTC in storage, team timezone on display, one shared date formatting path |
| Audit table growth with poor indexing | Slowing the team feed as data ages | The indexes in [04](04-data-model.md), cursor pagination, summary snapshots |
| Scope creep through "small" features | MVP never ships | The out-of-scope table in [02](02-mvp-scope.md) is the contract; a new feature enters only by removing another |

## Part 4: Open questions, with recommended defaults

None of these block planning: every one has a default that can be changed later at
a stated cost.

| # | Question | Recommended default | Cost to change later |
|---|---|---|---|
| 1 | Tech stack and hosting | TypeScript end to end: Next.js (App Router) + Postgres + a typed data layer + Tailwind; domain logic in a framework-free package. See [10](10-implementation-sequence.md) | Medium if the domain package is framework-free; high if not |
| 2 | Authentication method | Email + password, invite codes for joining, no SSO, no social login in MVP 1 | Low |
| 3 | How the team joins | Team invite code plus email invites; guests need a name only | Low |
| 4 | Deployment target | A single small managed host with Postgres, plus object storage later | Low |
| 5 | Can guests become members? | Yes, via a claim flow; history is reattributed as an audited event | Low |
| 6 | Do ideas need voting? | No in MVP 1 | Low |
| 7 | Kiswahili in the UI? | English UI with Kenyan context and a few well-understood Kiswahili words; do not invent terms | Low if term choices live in one place |
| 8 | Season length | One quarter, named ("Kika Season 1") | Low |
| 9 | XP opt-out visibility | Private: opted-out people simply do not appear, no explanation required | Low |
| 10 | Per-phone game play in 1.0? | No | Medium; the schema already supports it |
| 11 | One daily digest email? | Yes, and it is the only notification in MVP 1 | Low |
| 12 | `cancelled` session status? | Yes | Low |
| 13 | Can a member close a session? | Only a session they created or facilitate | Low |
| 14 | Are comments needed on every entity? | Only idea, decision, task, blocker, session. Not projects in 1.0 | Low |
| 15 | Do we allow unowned tasks? | Yes, in `backlog` only | Low |
| 16 | Should the summary be editable? | No. Regenerate instead, and keep the previous snapshot as superseded | Medium if people demand editing |
| 17 | Offline mode? | Out of scope; tolerate flakiness, do not promise offline | High |
| 18 | Who owns content authoring? | A named person, budgeted in Phase 4. Not "whoever has time" | Low, but the content is the product |

## Part 5: If you have to cut

Priority order for cutting, if the timeline tightens. Cut from the middle of this
list, never the top or the bottom.

**Never cut:** auth and team basics, the audit trail, session Run Mode, ideas,
decisions, tasks with origins, the session summary text export, My Work.

**Cut in this order:**

1. Task board (keep the list)
2. Projects (keep session-scoped tasks and labels)
3. Achievements (keep XP and standings)
4. Leaderboard seasons (keep the per-session standings)
5. Games beyond a single prompt deck
6. Global activity filters (keep the session feed)
7. Search
8. Blockers as an entity (demote to a status plus a required note, which costs the
   Firefighter achievement)

The point of this list is that the meeting loop survives every cut. If a cut breaks
the loop, it is not a cut, it is a smaller product.
