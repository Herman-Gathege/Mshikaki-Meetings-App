# 12 - Decision Log

Every decision in this package, in one place, with a stable ID so `/plan`, ADRs and
later reviews can cite them. The decisions themselves live in the referenced
documents; this is the index and the status.

**Status values:** `decided` (this package recommends it and it is reflected in the
model), `recommended` (a default chosen for planning; you should confirm),
`open` (needs your input before Phase 1).

| ID | Decision | Status | Reference |
|---|---|---|---|
| D1 | The meeting loop (PLAY -> ... -> RECORD) is the product; CRUD modules support it | decided | [01](01-product-definition.md) |
| D2 | Session Run Mode is the centrepiece vertical slice and is built first | decided | [05](05-journeys-ia-permissions.md), [10](10-implementation-sequence.md) |
| D3 | Project -> Task only; no `Group` entity in MVP 1, labels instead | decided | [03](03-domain-model.md), [09](09-risks-and-open-questions.md) #2 |
| D4 | Tasks link to their *originating* session; sessions do not contain tasks | decided | [03](03-domain-model.md), [09](09-risks-and-open-questions.md) #3 |
| D5 | Blockers are first-class entities as well as a task status | decided | [03](03-domain-model.md) |
| D6 | Decisions have no approval workflow; they are recorded and may be superseded | decided | [03](03-domain-model.md) |
| D7 | No voting on ideas in MVP 1 | decided | [02](02-mvp-scope.md) |
| D8 | Session statuses: planned, active, paused, completed, cancelled; one active per team | decided | [03](03-domain-model.md) |
| D9 | Task statuses: backlog, in_progress, blocked, done, cancelled; owner required for any non-backlog state | decided | [03](03-domain-model.md) |
| D10 | Ideas have statuses new, discussing, accepted, parked, rejected, converted | decided | [03](03-domain-model.md) |
| D11 | Games: one engine, three families, two playable formats in MVP 1 | decided | [06](06-games.md) |
| D12 | No per-phone realtime game play in MVP 1; schema reserves room for it | decided | [06](06-games.md), [09](09-risks-and-open-questions.md) #1 |
| D13 | The host can always override a score, and every override is audited | decided | [06](06-games.md) |
| D14 | Games open the meeting and are never used for evaluation | decided | [07](07-leaderboard-xp.md) |
| D15 | XP is an append-only ledger with caps; the leaderboard is a query, never a stored counter | decided | [07](07-leaderboard-xp.md) |
| D16 | Every person can opt out of the leaderboard; serious metrics are separate and unscored | decided | [07](07-leaderboard-xp.md) |
| D17 | Attendance, play and accepted ideas earn XP; comments and logins earn nothing; task creation earns nothing | decided | [07](07-leaderboard-xp.md) |
| D18 | Activity is append-only, whitelist-driven, and enforced by database grants | decided | [08](08-audit-trail.md) |
| D19 | Activity records store human-readable titles and old/new values, not only IDs | decided | [08](08-audit-trail.md) |
| D20 | Viewing, searching and typing are never recorded | decided | [08](08-audit-trail.md) |
| D21 | The session summary is a frozen snapshot generated at close, rule-based, no LLM | decided | [08](08-audit-trail.md) |
| D22 | Plain-text summary export is P0, because WhatsApp is where the team actually shares things | decided | [08](08-audit-trail.md) |
| D23 | Exactly one notification in MVP 1: a daily digest email | recommended | [09](09-risks-and-open-questions.md) #7 |
| D24 | Guests are first-class session participants with no account, claimable later | decided | [03](03-domain-model.md) |
| D25 | Four team roles: owner, admin, facilitator, member; facilitator power is session-scoped | decided | [05](05-journeys-ia-permissions.md) |
| D26 | Authors can always edit their own content; admins edit with attribution rather than silently | decided | [05](05-journeys-ia-permissions.md) |
| D27 | Deletion is soft and audited; hard delete is admin-only | decided | [03](03-domain-model.md) |
| D28 | Erasure anonymises the person, not the history | decided | [08](08-audit-trail.md) |
| D29 | Postgres, soft delete, UUIDv7 IDs, `text` + check constraints for statuses | decided | [04](04-data-model.md) |
| D30 | Organisation -> team -> membership exists from the first migration, but there is no multi-team UI | decided | [03](03-domain-model.md), [09](09-risks-and-open-questions.md) #13 |
| D31 | Two layout modes: screen-first for Run Mode and games, mobile-first for capture and work | decided | [05](05-journeys-ia-permissions.md), [09](09-risks-and-open-questions.md) #8 |
| D32 | No realtime in MVP 1; short polling in Run Mode | decided | [09](09-risks-and-open-questions.md) #9 |
| D33 | Content packs must declare a license and attribution; no lyrics or film quotes | decided | [06](06-games.md) |
| D34 | Web app only; no native apps in MVP 1 | decided | [02](02-mvp-scope.md) |
| D35 | The out-of-scope table in doc 02 is a contract; new scope enters only by removing scope | decided | [02](02-mvp-scope.md) |
| D36 | Tech stack: TypeScript end to end (Next.js + Postgres + typed data layer + Tailwind) | open | [10](10-implementation-sequence.md) |
| D37 | Authentication: email + password plus invite codes; no SSO or social login in MVP 1 | recommended | [09](09-risks-and-open-questions.md) #2 |
| D38 | Domain logic lives in a framework-free package, tested without a database | recommended | [10](10-implementation-sequence.md) |
| D39 | Season length: one quarter, named, with all-time as a low-prominence secondary board | recommended | [07](07-leaderboard-xp.md) |
| D40 | English-first UI with Kenyan context; no invented Kiswahili terms | recommended | [09](09-risks-and-open-questions.md) #7 |
| D41 | One auto-created organisation and team at setup; no org-switching UI | decided | [03](03-domain-model.md) |
| D42 | Six project agent skills, created progressively, not upfront | recommended | [11](11-agent-skills.md) |

## How to use this with `/plan`

1. Walk the `open` and `recommended` rows and either accept or overrule each one.
2. Turn each accepted row into a plan item under the phase in
   [10](10-implementation-sequence.md) where it belongs.
3. Anything that changes a `decided` row should also update the document that
   states it, in the same change. A decision log that disagrees with the model is
   worse than no log.
