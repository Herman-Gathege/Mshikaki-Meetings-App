# Mshikaki MVP 1 - Discovery Package

This document set is the output of the discovery goal: understand and structure
Mshikaki MVP 1 **before** writing significant application code.

No application code exists yet. Nothing here is final - the point is to give you a
concrete, opinionated thing to disagree with.

## Reading order

| # | Document | Answers |
|---|---|---|
| 01 | [Product definition](01-product-definition.md) | What is this, for whom, why would anyone use it |
| 02 | [MVP 1 scope](02-mvp-scope.md) | In, out, deferred, and what "done" means |
| 03 | [Domain model](03-domain-model.md) | Entities, relationships, state machines, invariants |
| 04 | [Data model](04-data-model.md) | Tables, columns, indexes, tenancy, seed data |
| 05 | [Journeys, IA and permissions](05-journeys-ia-permissions.md) | Screens, flows, roles, capability matrix |
| 06 | [Game architecture](06-games.md) | One engine, many game types, content and licensing |
| 07 | [Leaderboard and XP](07-leaderboard-xp.md) | Fun without becoming a performance review |
| 08 | [Audit trail](08-audit-trail.md) | The real reason this product exists |
| 09 | [Risks and open questions](09-risks-and-open-questions.md) | What is unclear, contradictory or expensive |
| 10 | [Implementation sequence](10-implementation-sequence.md) | Order of work, phases, exit criteria |
| 11 | [Agent skills](11-agent-skills.md) | The small skill ecosystem for this repo |
| 12 | [Decision log](12-decision-log.md) | D-numbers for every choice, for `/plan` to cite |
| 13 | [Plan brief](13-plan-brief.md) | The single condensed report to hand to `/plan` |
| 14 | [Implementation plan](14-implementation-plan.md) | The MVP 1 plan: architecture, repo shape, deployment, and every phase's tickets |
| 15 | [Phase 6](15-phase-6.md) | The current phase: human UX, play experience and hardening |
| 16 | [UX audit](16-ux-audit.md) | Where the app made people think, and what changed |
| 17 | [UX and rehearsal](17-ux.md) | Voice, visual language, Run Mode, the question lifecycle and the rehearsal checklist |
| 18 | [UX verification](18-ux-verification.md) | The measured accessibility and bad-connection evidence, and how to re-run it |
| 19 | [Agenda-led meetings](19-agenda-meetings.md) | The agenda as the meeting backbone, notes, outcomes and the PDF minutes |
| 20 | [User test feedback plan](20-user-test-feedback-plan.md) | What the first user test found, verified against the code, and how each item would be built |

If you only want to plan, read **[13-plan-brief.md](13-plan-brief.md)** on its own.
It restates everything a plan needs and points back to the detail documents.

## How to review this

Read 01, 02 and 09 first. Those three carry the product argument and the
disagreements. The rest is structure that follows from them and is cheap to
change while nothing is built.

Review 09 last-but-carefully: it is the list of places where the original concept
was ambiguous, and each item has a **recommended default** so none of them block
planning. Accept a default, or overrule it - either way it becomes a decision in
[12-decision-log.md](12-decision-log.md).

## The five things most likely to change your plan

These are the recommendations in this package that depart most from the original
brief. Everything else is elaboration.

1. **The meeting loop is the product; the CRUD is supporting cast.** Build the
   Session Run Mode as one vertical slice end to end (play -> capture -> decide ->
   assign -> close -> summary) before building breadth across projects, ideas and
   games as separate modules. See [10](10-implementation-sequence.md).
2. **MVP 1 plays games on one shared screen, not on every phone.** A realtime
   multiplayer engine is roughly as much work as the rest of MVP 1 combined. The
   data model reserves room for per-phone play; the UI does not ship it in 1.0.
   See [06](06-games.md).
3. **Drop `Group` from MVP 1.** `Project -> Task` plus labels. A third nesting
   level is a mobile navigation tax paid before anyone has asked for it. See
   [03](03-domain-model.md).
4. **One notification, or the audit trail dies unread.** "No notifications" is
   coherent as a scope decision and fatal as a product decision. MVP 1 ships
   exactly one: a short daily digest. See [09](09-risks-and-open-questions.md).
5. **XP needs caps and an opt-out on day one.** A leaderboard that rewards closing
   tickets without doing work, or that doubles as a performance review, will be
   resented within a month. See [07](07-leaderboard-xp.md).

## What is deliberately not here

- No application code, no scaffolding, no dependency choices committed to a
  lockfile. Phase 1 of [10](10-implementation-sequence.md) does that.
- No pixel-level designs. [05](05-journeys-ia-permissions.md) defines screens,
  flows and rules, not mockups.
- No skill files created. [11](11-agent-skills.md) recommends the ecosystem and
  the order to create it in; skills should be created when the phase that needs
  them starts, not upfront.
