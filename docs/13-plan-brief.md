# 13 - Plan Brief (single input for /plan)

This is the condensed, self-contained report. It is the only document that needs to
be read to plan MVP 1. Documents 01-12 remain authoritative for detail; where this
brief and a detail document disagree, the detail document wins and the brief is
wrong.

**How to use it:** resolve the open decisions in section 3 (or accept the defaults),
then hand this file to `/plan`.

---

## 1. What we are building

Mshikaki is a small web app where a team plays a short game to warm up, then turns
the conversation that follows into ideas, decisions and assigned work - with an
automatic record of who did what.

The one loop:

```text
PLAY -> CONNECT -> THINK -> DISCUSS -> DECIDE -> ASSIGN -> DO -> RECORD
```

Fun is the wedge. The audit trail is the value. First real user: the Innovations
ICT team. Design targets any team of 5-25 that meets regularly with a facilitator.

Positioning guardrail: not Jira, not Trello, not Notion, not Slack, not Kahoot, not
a performance system. Eight steps, one flow, no suite.

## 2. Fixed decisions (the contract)

These are settled. `/plan` should build on them, not re-open them.

| Theme | Decision | IDs |
|---|---|---|
| Product shape | The meeting loop is the product; CRUD modules support it. Session Run Mode is the centrepiece and is built first, as one vertical slice | D1, D2 |
| Work structure | `Project -> Task` only, no `Group` entity; labels instead. Tasks link to their **originating** session and are not contained by it | D3, D4 |
| Statuses | Session: planned, active, paused, completed, cancelled (one active per team). Task: backlog, in_progress, blocked, done, cancelled. Idea: new, discussing, accepted, parked, rejected, converted | D8, D9, D10 |
| Blockers | First-class entities plus a task status; a blocked task must have an open blocker | D5 |
| Decisions | No approval workflow. Recorded agreements that may be superseded | D6 |
| Ideas | No voting in MVP 1 | D7 |
| Games | One engine, three families (`prompt_deck`, `host_quiz`, `host_scored`), two playable formats in 1.0. Host can always override a score, and overrides are audited. No per-phone realtime | D11, D12, D13 |
| XP and leaderboard | XP is an append-only ledger with caps; the leaderboard is a query, never a stored counter. Comments, logins and task creation earn nothing. Every person can opt out. Serious metrics are separate and unscored | D14, D15, D16, D17 |
| Audit trail | Append-only, whitelist-driven, enforced by database grants. Records store human-readable titles and old/new values, not only IDs. Viewing, searching and typing are never recorded | D18, D19, D20 |
| Session summary | Frozen snapshot generated at close, rule-based, no LLM. Plain-text export is P0 | D21, D22 |
| People | Guests are first-class session participants with no account, claimable later. Four roles: owner, admin, facilitator, member; facilitator power is session-scoped | D24, D25 |
| Content rules | Authors edit their own content; admins edit with attribution. Deletion is soft and audited; hard delete is admin-only; erasure anonymises the person, not the history | D26, D27, D28 |
| Platform | Postgres, soft delete, UUIDv7 IDs, `text` + check constraints for statuses. `organisation -> team -> membership` from the first migration, no multi-team UI. Web only, no native apps. Two layout modes: screen-first for Run Mode and games, mobile-first for capture and work. No realtime; short polling in Run Mode. Content packs must declare a license and attribution | D29, D30, D31, D32, D33, D34, D41 |
| Discipline | The out-of-scope table in doc 02 is a contract. New scope enters only by removing scope. Domain logic lives in a framework-free package tested without a database | D35, D38 |

## 3. Open decisions - resolve before or during planning

Each has a working default. Nothing here blocks planning; accepting the defaults is
a valid answer.

| # | Decision | Recommended default | ID |
|---|---|---|---|
| 1 | Tech stack | TypeScript end to end: Next.js (App Router) + Postgres + typed data layer + Tailwind, with domain logic in a framework-free package. Alternatives documented in doc 10 | D36 |
| 2 | Authentication | Email + password plus invite codes; no SSO, no social login in MVP 1 | D37 |
| 3 | Notifications | Exactly one: a short daily digest email. This is a deliberate exception to "no notifications" | D23 |
| 4 | Season length | One quarter, named; all-time board as low-prominence secondary | D39 |
| 5 | Language and voice | English-first with Kenyan context; no invented Kiswahili terms | D40 |
| 6 | Project skills | Create two project skills, progressively, not upfront | D42 |

```text
DECISION NEEDED:  D36 (stack) is the only one that changes the shape of the plan.
                  Confirm it, or choose Alternative A (Supabase) or B
                  (Django + DRF + HTMX) from doc 10.
```

## 4. MVP 1 scope

**In:** sessions with a status lifecycle and Run Mode; a game library with two
playable formats; ideas with capture and promotion; decisions; tasks with owners,
blockers and two views; flat projects; automatic activity trail; XP, achievements
and a seasonal leaderboard; a generated session summary with plain-text export.

**Out (deferred, deliberately):** per-phone realtime play, chat, calendar sync,
file attachments, AI assistants, notifications beyond the digest, native apps,
offline-first sync, QR joining, external participants, team-vs-team, custom
workflows and fields, org-wide reporting, SSO, integrations, idea voting, blockers
as a separate board, recurring session series, live reactions.

**Definition of done for MVP 1:** a facilitator plans and runs a real session
without help; guests can play without accounts; ideas, decisions and tasks are
capturable in under five seconds each from a phone; every task has an owner, a
status and a visible origin; closing a session produces an accurate summary with no
human editing; every action appears in the audit trail automatically; a newcomer
can walk Task -> Decision -> Idea -> Session; the leaderboard is fun, capped and
opt-out-able; it works on a slow phone connection and a shared screen; nobody had
to be trained.

## 5. Domain model at a glance

Three layers:

1. **Tenancy and people:** organisation, team, membership, user, invite, guest.
2. **The loop:** session, session_participant, agenda_item, game_definition,
   content_pack, game_question, game_play, game_score, idea, idea_tag, decision,
   project, task, task_collaborator, blocker, comment.
3. **The record:** activity, xp_rule, season, xp_event, achievement,
   achievement_award, notification (reserved).

```text
Session ----> Idea ---> Decision ----> Task <--- (one owner, collaborators)
   |            \          |            |
   v             \         |            v
GamePlay       Comment    Comment    Blocker
   |                                   |
   +---------------> Activity <--------+
                       ^
                       |
                 XP event -> Achievement -> Leaderboard
```

**Invariants (enforce in code, DB where possible, test in CI):**

1. Every mutation writes an activity record through one shared helper.
2. Activity, xp_events and achievement_awards are append-only; the app's DB role has no UPDATE or DELETE.
3. Every domain row is team-scoped and every query filters by `team_id`.
4. Exactly one owner per task; collaborators are separate rows.
5. A task in `blocked` must have an open blocker; a task may be unowned only in `backlog`.
6. A closed session has a frozen summary; regeneration is explicit and audited.
7. XP is derived from the ledger and every award is idempotent.
8. Deletion is soft and audited; hard delete is admin-only.
9. Guests are participants, players and collaborators, but cannot log in until they claim a profile.
10. Origin links are permanent: a task keeps its session, idea and decision links forever.

## 6. Permissions

Roles: `owner`, `admin`, `facilitator`, `member`, plus session-scoped `guest`.

Principles: authorship beats hierarchy for content (a member can always edit their
own idea; admins edit with attribution rather than silently); facilitator power is
scoped to sessions they facilitate and expires at close; guests are constrained by
scope, not by extra roles; permission denials are logged; nothing is hard-deleted
by a normal user. The full capability matrix is in doc 05 and should become the
permission test suite.

## 7. Audit trail requirements

Six things it must do: **automatic** (no user action produces a record),
**complete** (every create, update, status change, assignment, comment, delete and
restore on a tracked entity), **attributed** (user, credited guest or system),
**immutable**, **contextual** (readable as a sentence with old and new values), and
**traversable** (per entity, per session, per team, with filters).

Governed by a verb whitelist, not an event firehose. Anything not on the list -
views, searches, typing, presence, notification reads - is never recorded. Display
coalesces rapid edits; storage never does. Three reads of the same data: entity
activity, session activity, team activity.

## 8. Game architecture

One engine, three families, two playable in MVP 1:

| Family | MVP 1 | Examples |
|---|---|---|
| `prompt_deck` | playable | rapid-fire, funny icebreakers, "name 5 things" |
| `host_quiz` | playable, host-paced, host confirms answers | trivia (general, Kenyan, sports, geography, history), true/false, emoji, "who said it?", picture, riddles |
| `host_scored` | catalogue plus manual score entry | judged activities, charades-style, team challenges |

Timer, teams, rounds and difficulty are modifiers, not families. Adding a game type
later must require a definition row and content only, never a migration.

Content budget for launch: roughly 200 items across 3 trivia packs, a true/false
set, an emoji/picture set, 3 prompt decks and one host-scored activity - each with
a declared license and attribution, original content preferred, roughly half local
and half global. Content authoring is a budgeted deliverable with a named owner.

## 9. Leaderboard and XP

Ledger-based, capped, opt-out-able, never a performance measure. Permanent
on-screen disclaimer. Serious metrics live in a separate, unscored view. XP for
attendance, play, winning, ideas submitted, ideas accepted, decisions recorded,
tasks completed and blockers resolved - with caps per session, day and week, plus
diminishing returns, facilitator weighting at 0.5 for structural actions, and
idempotent awards. Nothing for logins, edits, comments or task creation. Never show
a bottom-of-the-table list.

## 10. Phases

| Phase | Goal | Key deliverables | Exit criteria | Depends on |
|---|---|---|---|---|
| **0. Decide and scaffold** | Convert this package into an agreed plan | Resolve open decisions; first two ADRs; repo skeleton (app, domain package, migrations, CI, `.env` conventions); `AGENTS.md` with the invariants; `CONTEXT.md`; `docs/standards.md`; run `setup-matt-pocock-skills` | Every open question has a decision or explicit deferral; the repo builds and deploys a hello-world page; invariants are written where agents read them | this brief |
| **1. Foundation** | Identity, tenancy and the record spine. Nothing fun | Auth (email + password, invite codes); organisation/team/membership/roles/invites; one testable permission function used by every route; the activity spine (table, single write helper, verb whitelist, shared sentence formatter, entity activity component); design system and mobile-first shell; guests; seeded game definitions and one small content pack | Two users in one team log in, see each other, and every mutation appears in an attributed, immutable, team-scoped activity feed. A test proves cross-team reads fail | Phase 0 |
| **2. Meeting loop, end to end** | Run a real meeting in the app, start to finish, even if everything else is missing | Sessions with the full status lifecycle; **Run Mode**; agenda; ideas; decisions; tasks with origin links and blockers; one playable prompt deck; session summary snapshot + plain-text export; traceability in both directions | A real session runs without help; at least one decision and three assigned tasks; the summary is accurate with no editing; the text export can be pasted into WhatsApp; every object traces to the session | Phase 1 |
| **3. Work layer** | Make the week between meetings work | My Work grouped by urgency; flat projects with linked decisions, ideas and activity; task list with filters; simple board; blockers raise/resolve and surface to the team; comments on tasks and blockers; unscored serious metrics | A task created in a session is worked, blocked, unblocked and completed without returning to the session, with the whole story on its activity feed | Phase 2 |
| **4. Play layer** | Make it fun enough that people ask for it | Game library with filters; the `host_quiz` renderer on the same engine; the starter content packs; XP rules, caps and ledger; achievements; leaderboard (session, season, all-time, opt-out, disclaimer); the daily digest email | A session with two games, scored, with standings and XP; no repeatable action earns unbounded points; an opt-out is handled correctly | Phases 2-3 |
| **5. Traceability and adoption** | Make the promise real | Back-links ("why does this exist?") everywhere; global activity with filters; search over ideas, decisions, tasks; onboarding, empty states, sample session, the record charter; summary rendering polish; guest claiming and history reattribution | Someone who has never used the app answers "what did we decide about X and who is doing it" within two minutes of landing on Today | Phase 3 |
| **6. Hardening** | Survive a real room | Performance on a throttled connection; accessibility and projector contrast; permission, tenancy and audit-immutability tests; backups with a rehearsed restore; error tracking and structured logs; a full rehearsal | A real session runs on a bad connection in a real room and nothing needs explaining twice | Phase 4-5 |

Effort shape to protect the loop: foundation ~25%, session and Run Mode ~25%, work
layer ~20%, play layer ~20%, content, polish and hardening ~10%. If the play layer
exceeds its share, cut game types, not dates.

## 11. Skills and repo configuration

Do now, in Phase 0, as configuration rather than skills: `AGENTS.md` holding the
invariants (always in context, unlike a skill), `CONTEXT.md` holding the domain
vocabulary (written with the existing `domain-modeling` skill), and
`docs/standards.md` so the existing `code-review` skill reviews against this repo's
standards.

Create exactly two project skills, and only when their phase arrives:
`mshikaki-content-pack` (Phase 4, with a pack validator script) and
`mshikaki-session-rehearsal` (Phase 2 exit or Phase 6). A third,
`mshikaki-game-type`, waits until a second engine is approved.

Do not create product, architecture, frontend, database, backend, security, testing
or review skills: they are already covered by `tdd`, `to-spec`, `to-tickets`,
`triage`, `implement`, `codebase-design`, `domain-modeling`, `prototype`,
`wayfinder`, `research` and `code-review`, and parallel skills would only create a
second place for the same rule to drift. Full reasoning in doc 11.

## 12. Risks that must shape the plan

| Risk | Plan response |
|---|---|
| Games are the largest cost and least connected to the value | Fixed family count, one engine, no realtime; play layer is last and cuttable |
| Phase 1 expands forever | Phase 1 ends when two users can record activity, not when the design system is beautiful |
| Model mistakes surface in Phase 2 | Lock the core entity model before Phase 2 starts; expect churn only there |
| The facilitator becomes a laptop operator | Run Mode = one action per step, keyboard shortcuts, phone control strip |
| WhatsApp remains the real record | Plain-text summary export is P0 and is designed for pasting |
| Nobody returns between meetings | My Work on Today plus the one digest email; no streaks or guilt mechanics |
| The audit trail feels like surveillance | Record charter on onboarding; no views, reading, typing or presence recorded; per-person leaderboard opt-out |
| An audit trail with holes | Single write helper, DB grants, one integration test per entity asserting the activity row |
| Bad connectivity in the room | Host-side content preload, local scoring, optimistic writes, no hard network dependency in the fun layer |
| Content licensing | License and attribution are non-null; no lyrics or film quotes; a review step before a pack ships |

## 13. Success criteria

**Adoption:** one full session run start to finish with no parallel notebook or
WhatsApp thread; the facilitator needs no help; first task assigned within 45
minutes of a real meeting.

**Output:** the auto-generated summary is good enough to send unedited to someone
who missed the meeting; 80% of tasks still have a live owner and accurate status two
weeks later; every task traces to a session; zero manual minute-writing.

**Engagement:** a game is played in a majority of sessions that go active, without
being prompted; the leaderboard is used voluntarily and nobody calls it
surveillance.

**Anti-criteria:** the team keeps the real record elsewhere; the facilitator is
buried in the laptop; the trail is never read; a dropped week leaves an
unreconstructable hole; the leaderboard changes behaviour on real work in a way
people resent.

## 14. What the plan should produce

1. A Phase 0 checklist with the six open decisions resolved and ADRs written.
2. Per phase: deliverables broken into tickets with explicit dependencies, sized,
   and each stating its own acceptance test.
3. The first vertical slice (Phase 2) decomposed finely enough to start - it is the
   risk-bearing part.
4. The permission matrix and the invariant list converted into named test suites.
5. A content-authoring workstream with an owner and a count.
6. Named risks with a trigger that says when to cut scope, per doc 09.
7. Explicitly out of scope, restated, so nothing creeps in.

## 15. Ready-to-paste `/plan` prompt

```text
/plan

Plan Mshikaki MVP 1 using docs/13-plan-brief.md as the authoritative input
(detail lives in docs/01-12; the brief is wrong if they disagree).

Context: a playful collaboration app where a team plays a short game, then turns
the discussion into ideas, decisions and assigned work, with an automatic audit
trail. The loop is PLAY -> CONNECT -> THINK -> DISCUSS -> DECIDE -> ASSIGN -> DO ->
RECORD. First user is the Innovations ICT team; the architecture must stay
general beyond it.

Constraints:
- Do not re-open the fixed decisions in section 2 of the brief.
- Do not plan anything in the out-of-scope list in section 4.
- Build one vertical slice through the meeting loop (Phase 2) before widening.
- Every mutation writes an activity record; activity is append-only and enforced
  by database grants.
- XP is an append-only ledger with caps, never a stored counter.
- No realtime in MVP 1. No per-phone game play. No AI in the summary.
- Domain logic lives in a framework-free package testable without a database.
- Mobile-first at 360px, with Run Mode as the one screen-first exception.

Deliver:
1. Phase 0 checklist with the six open decisions resolved and the first ADRs
   listed.
2. For each phase 0-6: deliverables as tickets with explicit dependencies and an
   acceptance test per ticket, sized S/M/L.
3. Phase 2 decomposed finely enough to start immediately - list the specific
   tickets in build order.
4. The permission matrix and the invariant list expressed as named test suites.
5. A content-authoring workstream with an owner and item counts.
6. Named risks with a scope-cut trigger for each.
7. A restated out-of-scope list.

Note: my stack decision is ______ (default: TypeScript end to end - Next.js,
Postgres, typed data layer, Tailwind). Everything else: accept the brief's
recommended defaults unless the plan gives a concrete reason not to.
```
