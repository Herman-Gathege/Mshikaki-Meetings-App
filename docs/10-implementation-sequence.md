# 10 - Recommended Implementation Sequence

## The guiding rule

**Build one vertical slice through the meeting loop, then widen.**

The tempting alternative - build all the entities, then all the screens, then wire
them together - produces a system where nothing is usable until everything is
done, and where the loop's real problems appear last. Instead: Session #1 with one
game, one idea, one decision, one task and one summary, end to end, as early as
possible. Then add projects, then games, then gamification.

Corollary: the sequence is chosen so that after **Phase 2** you could run a real,
ugly, useful meeting.

## Phase 0 - Decisions and scaffolding (this goal, then `/plan`)

**Goal:** convert this package into an agreed, decided plan.

- Review [09](09-risks-and-open-questions.md) and settle the open questions.
- Record the outcomes in [12-decision-log.md](12-decision-log.md).
- Confirm the stack (open question 1) and write the first two architecture decision
  records.
- Create the repository skeleton: app, domain package, migrations, CI, `.env`
  conventions, an `AGENTS.md` with the invariants from [03](03-domain-model.md).
- Do not build features. Do not build a "foundation framework".

**Exit criteria:** every open question in [09](09-risks-and-open-questions.md) has a
decision or an explicit deferral; the repo builds and deploys a hello-world page;
the domain invariants are written down in a place agents will read.

## Phase 1 - Foundation

**Goal:** identity, tenancy and the record spine. Nothing fun yet.

- Auth: email + password, invite codes, session handling.
- Organisation, team, membership, roles, invites. One auto-created team at setup.
- The permission layer: a single, testable "can this actor do this to this object"
  function, used by every route. Not scattered checks.
- **The activity spine**: activity table, the single write helper, the whitelist of
  verbs, the shared human-readable formatter, the entity activity component, the
  session and team feeds.
- Design system: typography, spacing, buttons, form fields, empty states, the
  mobile-first layout shell. Ugly-but-consistent beats pretty-but-inconsistent.
- Guests: a participant identity that exists without an account.
- Seeded game definitions and one small content pack, so Phase 2's Play step has
  something to show.

**Exit criteria:** two users in one team can log in, see each other, and every
create/update they perform appears in an activity feed that is attributed,
immutable, and correctly scoped to the team. A test proves cross-team reads fail.

**Deliberately not yet:** projects, ideas, decisions, tasks, games, XP.

## Phase 2 - The meeting loop, end to end (the vertical slice)

**Goal:** run a real Innovations meeting in Mshikaki, start to finish, even if
everything else is missing.

- Sessions: create, plan, invite, start, pause, close, reopen.
- **Run Mode**: the guided step sequence with one action per step, plus the shared
  quick-capture sheet.
- Agenda items.
- Ideas: quick capture, list, detail, status transitions, comments.
- Decisions: record from an idea or standalone, link, supersede.
- Tasks: create with owner and due date, link to session/idea/decision, statuses,
  the blocker entity.
- One playable `prompt_deck` game during Run Mode, with results recorded.
- **Session summary**: generated at close, stored as a snapshot, rendered in-app,
  exportable as plain text.
- The traceability walk in both directions.

**Exit criteria:** a real session is run by the facilitator without help; by the
end there is at least one decision and three assigned tasks; the summary is
accurate without editing; the plain-text export can be pasted into WhatsApp; every
object created can be traced to the session. This is the point at which MVP 1
becomes genuinely useful, and it should arrive as early as possible.

## Phase 3 - The work layer

**Goal:** make the week between meetings work, because that is where retention
lives.

- My Work: owned tasks grouped by urgency, one-tap status changes.
- Projects: flat, with tasks, linked decisions, ideas and activity.
- Task list with filters; a simple board by status.
- Blockers: raise, resolve, surface to the team, and count in the summary.
- Comments on tasks and blockers.
- Serious metrics (unscored): completed, blocked, overdue, by owner.

**Exit criteria:** a task created in a session is found, worked, blocked, unblocked
and completed without ever going back to the session; the whole story is visible
on the task's activity feed.

## Phase 4 - The play layer

**Goal:** make it fun enough that people ask for it.

- Game library: browse, filter by time/energy/group size, launch from a session.
- The `host_quiz` renderer on top of the same engine: rounds, scoring, host
  override, standings.
- Content packs: the starter budget from [06](06-games.md), with license and
  attribution enforced.
- XP: rules table, caps, the ledger, idempotent award path.
- Achievements: definitions plus evaluation.
- Leaderboard: session, season, all-time, achievements, opt-out, disclaimer.
- The daily digest email (the one permitted notification).

**Exit criteria:** a full session with two games, scored, with standings and XP;
the leaderboard is capped against farming; no single action can be repeated for
unbounded points; someone has opted out and the system handles it correctly.

## Phase 5 - Traceability and adoption polish

- Back-link components ("why does this exist?") on every task, decision and idea.
- Global activity with filters; search across ideas, decisions, tasks.
- Onboarding: empty states, a sample session, the record charter from
  [09](09-risks-and-open-questions.md) item 10.
- Summary rendering polish, including print-friendly output if anyone asks.
- Guest claiming and history reattribution.

**Exit criteria:** a person who has never used the app can answer "what did we
decide about X and who is doing it" within two minutes of landing on Today.

## Phase 6 - Hardening

- Performance: Run Mode and Today on a throttled connection; bundle size; image
  and content payload sizes.
- Accessibility: focus order, contrast on the projector, screen reader labels on
  the capture flow.
- Security: permission tests per role, tenancy tests, rate limits on auth, audit
  immutability verified by attempting to write as the app role.
- Operations: backups and a rehearsed restore, error tracking, a health endpoint,
  structured logs, a documented deploy.
- A rehearsal: run a full session in the app with test data before running one for
  real.

**Exit criteria:** the team runs a real session on a bad connection in a real room
and nothing needs to be explained twice.

## Suggested repository shape

Monorepo-lite. The important part is not the tooling, it is that **domain logic is
framework-free and tested without a browser or a database.**

```text
apps/
  web/            # UI, routes, server actions or API routes
packages/
  domain/         # entities, state machines, invariants, progressions (pure)
  data/           # repositories, migrations, activity-write enforcement
  content/        # seed game packs and definitions as versioned JSON
  ui/             # shared components and the design system
docs/             # this package, ADRs, CONTEXT.md
```

Why the domain package matters here specifically: the rules that make Mshikaki
trustworthy - task state transitions, "blocked implies an open blocker", "every
mutation writes activity", XP caps - are exactly the rules that should be testable
in milliseconds without a running app. If they live in route handlers, they will be
tested inconsistently and will drift.

## Stack recommendation and the alternatives

**Recommended:** TypeScript end to end - Next.js (App Router) for the web app,
Postgres, a typed data layer (Prisma or Drizzle), Tailwind for the design system,
server-side actions or route handlers for the API, deployed to a small managed
platform with managed Postgres.

Why: one language, one type system across the loop, excellent server rendering for
a mobile-first app on slow connections, a huge ecosystem for forms and tables, and
easy hiring for an ICT team that will maintain it.

**Alternative A - Supabase (or equivalent BaaS):** Postgres, auth, storage and
realtime out of the box. Saves Phase 1 almost entirely. Costs: row-level security
becomes the permission layer instead of your own testable function, and the audit
enforcement described in [08](08-audit-trail.md) is harder to guarantee. If chosen,
keep activity writes in server-side functions, not directly from the client.

**Alternative B - Django + DRF + HTMX/Tailwind:** mature admin, mature auth,
excellent for a CRUD-heavy auditable app, and a Python stack that matches other
work in this environment. Costs: less pleasant for the Run Mode interaction design
and for shared type safety with the frontend.

**Not recommended for MVP 1:** a separate SPA plus API deployed independently
(doubles the auth and CORS surface for no benefit at this size), or a
microservices split (nothing here is independently scalable).

## Testing strategy

| Layer | What it covers | Notes |
|---|---|---|
| Domain unit tests | State machines, invariants, XP caps, summary generation | Fast, no I/O. This is where most tests should live |
| Data integration tests | Every mutation writes activity; tenancy scope; soft delete | One per entity, asserting the activity row exists and is correct |
| Permission tests | The capability matrix in [05](05-journeys-ia-permissions.md) | Every role, every capability, including denials |
| API tests | Validation, error shapes, idempotency | Include the double-award case |
| End-to-end smoke | The meeting loop: create session -> play -> idea -> decision -> task -> close -> summary | One test, run before every session |
| Manual rehearsal | A real session, bad network, real devices | Cannot be automated and matters most |

## Sequencing risks

- **Phase 1 can expand forever.** It ends when a two-user team can record
  activity, not when the design system is beautiful.
- **Phase 2 will reveal model mistakes.** Expect them. That is why nothing else is
  built yet, and why the core entity model should be locked before Phase 2 starts.
- **Phase 4 can eat the project.** If the play layer starts doubling its estimate,
  cut game types, not dates.
- **Phase 5 is not deferrable forever.** Traceability is the product's promise; if
  it is never polished, Mshikaki is a task list with trivia.
