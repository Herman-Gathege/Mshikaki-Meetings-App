# 11 - Recommended Agent Skills

## The short answer

**Create two project skills now. Configure three things instead of making skills
out of them. Do not create the other five you might be tempted to.**

This repo is being used to learn `/goal`, `/plan` and reusable skills, and the
installed skill library on this machine is already strong: `to-spec`, `to-tickets`,
`triage`, `implement`, `tdd`, `code-review`, `domain-modeling`, `codebase-design`,
`research`, `prototype`, `wayfinder`, `retro`, `writing-for-agents`. Most of what a
Mshikaki-specific skill would say is already covered by one of those. Adding a
parallel `mshikaki-frontend` or `mshikaki-testing` skill would not add capability,
it would add a second place where the same rule can drift.

So the discipline here is mostly **subtraction**: only encode knowledge that
exists nowhere else, and only for workflows that are sometimes relevant.

## The four-part test before creating a skill

A skill earns its place only if all four are true:

1. **Would a competent agent get this wrong without it?** If not, it is noise.
2. **Is it relevant only some of the time?** Always-on rules belong in `AGENTS.md`,
   which is loaded on every task; a skill is loaded only when it matches.
3. **Is the knowledge durable and owned by this project?** Temporary phase
   checklists do not belong in a skill.
4. **Is there no existing skill that already covers it?** If `tdd` covers it, use
   `tdd`.

## Tier 1: configure this instead of creating skills

These are the highest-value moves, and none of them is a skill.

### 1. `AGENTS.md` - the always-on invariants

Cross-cutting rules that must hold in *every* change belong here, because they must
be in context even when no skill fires. Draft content, drawn from
[03](03-domain-model.md) and [08](08-audit-trail.md):

```markdown
## Mshikaki invariants (non-negotiable)
- Every mutation writes an activity record through the single shared helper.
  Never insert activity rows directly from a route or service.
- Activity, xp_events and achievement_awards are append-only. No UPDATE, no DELETE.
- Every domain row is team-scoped. Every query filters by team_id.
- A task may be unowned only in `backlog`. Non-backlog states require an owner.
- A task in `blocked` state must have an open blocker row.
- XP is a ledger, never a stored total. Awards must be idempotent.
- Deletion is soft and audited. Hard delete is admin-only.
- Domain rules live in packages/domain and are tested without a database or browser.

## Working agreements

- Read docs/03-domain-model.md and docs/08-audit-trail.md before changing the
  schema or adding an entity.
- The out-of-scope table in docs/02-mvp-scope.md is a contract. New scope enters
  only by removing scope, and the change is recorded in docs/12-decision-log.md.
- Use `task`, never "action". Use `session` for meetings and `auth_session` for
  logins.
- No new dependency without a one-line rationale in the pull request.
- Mobile-first at 360px; Run Mode is the one screen-first exception.
```

Keep it under a page. An `AGENTS.md` nobody reads is worse than none, because it
looks like governance while enforcing nothing.

### 2. `CONTEXT.md` - the domain vocabulary

The glossary: Session, Run Mode, Idea, Decision, Task, Blocker, Activity, XP event,
Season, Achievement, Guest, Skewer, the three game families, and every status
value. Written and maintained with the existing **`domain-modeling`** skill, which
is exactly what it is for. Do not create a Mshikaki skill to hold vocabulary; hold
it in `CONTEXT.md` so every skill and every agent reads the same words.

### 3. `docs/standards.md` - so `code-review` has something to check against

The installed `code-review` skill reviews a diff along two axes: **Standards** (the
repo's documented standards) and **Spec** (the originating issue). It needs the
repo's standards document to exist. Write one covering: naming, file layout,
error handling, permissions checks, activity emission, test placement, and commit
conventions. Then `code-review` gives Mshikaki-specific reviews with no new skill
at all. This is the single highest-leverage configuration step in this list.

Also run the existing **`setup-matt-pocock-skills`** in this repo once, so `to-spec`,
`to-tickets`, `triage` and `code-review` have an issue tracker and triage
vocabulary to work against.

## Tier 2: the skills worth creating

Two now, one later. Nothing else.

### `mshikaki-content-pack`

**Why it exists.** Authoring game content is the part of Mshikaki that looks like
filler and is actually a legal and product risk: unlicensed lyrics, questions that
embarrass someone in the room, a pack that is entirely UK trivia for a Kenyan team.
Every pack must also satisfy a schema, declare a license, and be validated before
it ships. That is a repeatable workflow with a known failure mode, it is only
relevant when content is being produced, and nothing in the existing library
covers it.

**Owns.** Producing and validating `content_pack` and `game_question` data:
structure, licensing and attribution, tone, difficulty spread, local/global mix,
and the "never embarrassing" rule.

**Invoke when.** Adding or extending a game pack, importing content, adding a new
question category, or auditing existing packs.

**Inputs.** The game definition and family, the target size, language and audience,
the source of the material (original or licensed), and the desired mix of
categories and difficulty.

**Outputs.** A validated JSON pack file in `packages/content`, with non-null
license and attribution, plus a short summary: item count, category and difficulty
distribution, and anything deliberately excluded.

**Must not.** Must not invent or reproduce licensed lyrics, film quotes, or
third-party question banks. Must not change the content schema, the game
definition, or any application code. Must not ship a pack whose license field is
unknown or "unclear". Must not assume a question is culturally safe because it is
funny.

**Resources.** A `scripts/validate_pack.py` (or TS equivalent) that checks the
schema, required metadata and duplicate prompts; `references/content-rules.md` for
the licensing and tone rules; `assets/pack-template.json`.

### `mshikaki-session-rehearsal`

**Why it exists.** Mshikaki's real acceptance test is not a green test suite, it is
a live meeting. The failure modes are operational: a projected screen at the wrong
resolution, no connectivity mid-game, a facilitator who has never used the app, a
summary that generates but is wrong, an activity trail with a hole in it. Nobody
catches those by running unit tests, and every one of them is embarrassing in front
of the team. This skill makes the rehearsal a repeatable procedure instead of
improvisation.

**Owns.** Verifying the full loop end to end against realistic conditions before a
real session: create -> play -> capture -> decide -> assign -> work -> close ->
summary -> trace, on a throttled connection, at both phone and projector sizes,
with at least one guest and one late joiner.

**Invoke when.** Before the first real session, before any session where the loop
changed, and after any change to permissions, activity emission or summary
generation.

**Inputs.** A running environment with seed data (or the ability to create it), the
list of changes since the last rehearsal, and access to a real phone-class viewport
and a desktop projector-class viewport.

**Outputs.** A go/no-go report: each step of the loop with observed behaviour and
evidence, every mismatch filed as a defect with reproduction steps, a list of steps
that had to be skipped, and an explicit statement of what was *not* verified. Plus
a reset of any data the rehearsal created.

**Must not.** Must not declare ready on the basis of "the tests pass". Must not fix
defects silently inside the rehearsal and then report success, because that hides
the bug from review. Must not touch production data or run against the live team's
workspace. Must not test only the happy path on a fast connection.

**Resources.** `scripts/rehearse.md` or a scripted smoke runner; a checklist as
`references/meeting-day.md`; the throttle and viewport settings worth using.

### `mshikaki-game-type` - create later, when the second engine is approved

Hold this one until per-phone play or a third family is actually approved. Its job
will be the mechanics of adding a game type through configuration rather than
special-casing: definitions, config schema, renderer seam, scoring rules, host
override, and the test that proves no migration was needed.

If a game type ever requires a migration to add, that is the signal this skill is
needed.

## Tier 3: skills deliberately not to create

| Tempting skill | Why not | Use instead |
|---|---|---|
| `mshikaki-product` / product discovery | The generic discovery flow already exists and the product argument lives in docs 01-02, which are always visible | `/plan`, then `to-spec`, `grill-me`, `loop-me` |
| `mshikaki-architecture` | Duplicates vocabulary that belongs in one place | `codebase-design`, `wayfinder`, and `docs/03` |
| `mshikaki-frontend` / `mshikaki-ui` | Would restate a design system that must live as code and in `docs/design-system.md` | `prototype` for exploration, `implement` for building, plus a design-system doc |
| `mshikaki-database` | Would duplicate `domain-modeling` and the schema docs | `domain-modeling`, `docs/04`, and a migration checklist in `standards.md` |
| `mshikaki-backend` / `mshikaki-api` | The rules it would assert are invariants, so they belong in `AGENTS.md` where they are always loaded | `AGENTS.md`, `implement`, `tdd` |
| `mshikaki-security` | Security here is permissions and tenancy, which are testable, not advisory | Permission and tenancy test suites; `code-review` with standards |
| `mshikaki-testing` | Already covered, and a second testing skill will disagree with the first | `tdd`, plus the rehearsal skill for the operational layer |
| `mshikaki-audit` | Tempting and wrong: audit completeness is a property that must be enforced on every change, not invoked when someone remembers | `AGENTS.md` rule, the single activity write helper, and one integration test per entity |
| `mshikaki-code-review` | Would fork the review process into two inconsistent variants | Write `docs/standards.md` and let `code-review` read it |
| `mshikaki-docs` | Nothing Mshikaki-specific to say | `writing-for-agents`, `domain-modeling` |
| `mshikaki-project-management` | Generic tracker mechanics, not product knowledge | `to-tickets`, `triage`, `wayfinder`, `retro` |
| One skill per technology | Framework skills rot fastest and add nothing | The framework's own docs, read on demand |
| One skill per phase of doc 10 | Phase checklists are transient; they belong in the plan, not in permanent context | `/plan`, then tickets |

## Mapping the categories you asked about

| Category you named | Covered by |
|---|---|
| Product discovery | `to-spec`, `grill-me`, `loop-me`, docs 01-02 |
| Architecture | `codebase-design`, `wayfinder`, `docs/03`, ADRs |
| UI/UX | `prototype`, `docs/design-system.md`, `implement` |
| Database design | `domain-modeling`, `docs/04`, migration rules in `standards.md` |
| Frontend implementation | `implement`, `implement-spec`, `tdd` |
| Backend implementation | `implement`, `implement-spec`, `tdd` |
| Testing | `tdd` + `mshikaki-session-rehearsal` (new) |
| Security | Permission and tenancy tests, `code-review` standards |
| Code review | `code-review` + `docs/standards.md` |
| Documentation | `writing-for-agents`, `CONTEXT.md`, ADRs |
| Project management | `to-tickets`, `triage`, `wayfinder`, `retro` |
| **Game content** | **`mshikaki-content-pack` (new)** |
| **Meeting-day readiness** | **`mshikaki-session-rehearsal` (new)** |

## Where skills live, and what is writable

- Personal skills: `/home/remington/.agents/skills/` (the installed collection,
  including `tdd`, `to-spec`, `code-review`).
- System skills: `/home/remington/.codex/skills/.system/` and the bundled plugin
  caches.
- This repository already has `.agents/` and `.codex/` directories, but in the
  current session they are **read-only**, so project skills cannot be created here
  until write access is granted or they are created outside the sandbox.

Two decisions to settle in Phase 0:

1. **Repo-scoped or personal?** Repo-scoped skills (`.agents/skills/`) travel with
   the project and are the better fit for a product-specific skill like
   `mshikaki-content-pack`. Personal skills are easier when the skill is really
   yours across projects.
2. **Confirm discovery actually picks them up.** Whichever location is chosen,
   verify by creating one throwaway skill and checking it appears in the available
   skills list before writing the real ones.

## Creation order

1. **Now (Phase 0):** `AGENTS.md`, `CONTEXT.md`, `docs/standards.md`, run
   `setup-matt-pocock-skills`. No new skills.
2. **Phase 1:** nothing new. If the invariants keep getting missed, the fix is
   tests and `AGENTS.md` wording, not a skill.
3. **Phase 4, before content authoring starts:** `mshikaki-content-pack`, plus its
   validator script.
4. **Phase 2 exit / Phase 6:** `mshikaki-session-rehearsal`, once the loop exists to
   rehearse.
5. **When a second game engine is approved:** `mshikaki-game-type`.

Creating all of these on day one would be exactly the "pile of overlapping skills"
that this document exists to prevent. The trigger for each is a phase, not
enthusiasm.
