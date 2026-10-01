# Standards

What a reviewer should check. `code-review` reads this file for its Standards
axis, so keep it honest and current.

## Python

- Python 3.12, formatted and linted by Ruff (`make fmt`, `make lint`), line length
  100. No exceptions without a comment saying why.
- Type hints on every function signature. `from __future__ import annotations` at
  the top of modules that use modern syntax.
- Constants over literals: statuses come from `app.domain.enums`, verbs from
  `app.domain.activity`, capabilities from `app.domain.permissions`.
- No mutable default arguments, no bare `except:`, no `except Exception` without
  either re-raising or returning a stable error.

## Layering

```text
api/         HTTP only: validate, resolve the target, check the capability, call a service
services/    orchestration: load, call domain rules, persist, record activity
domain/      pure rules: no FastAPI, no SQLAlchemy, no I/O, no clock reads without injection
db/          models and session handling
```

- A router never contains a business rule or a status transition.
- A service never builds an HTTP response.
- Domain code never imports from the other three layers.
- Cross-module access happens through the service layer, not by reaching into
  another model.

## Database

- Every schema change is an Alembic migration. No manual edits, ever.
- Migrations are named `NNNN_verb_subject` and are not edited after they have been
  applied anywhere but the author's machine.
- Models and migrations must agree; `--autogenerate` producing a diff is a defect.
- Soft delete via `deleted_at`. Queries exclude deleted rows unless the feature is
  explicitly about history.
- Indexes are added with the query that needs them, and reviewed in the same
  change.

## API

- `/api` prefix, REST, `snake_case` JSON.
- Errors always use the shape from `app/errors.py` with a stable code.
- Collections are cursor-paginated: `?limit=&cursor=` returning
  `{items, next_cursor}`.
- Lifecycle changes are explicit endpoints (`POST /sessions/{id}/close`), not a
  generic status patch.
- Permissions are enforced with `require_capability` or `can()`. Routers never
  branch on a role.

## Activity, the rule that matters most

- Mutating services call `record_activity` inside the same transaction as the
  change they describe.
- The verb string must exist in the whitelist.
- The payload carries titles and old/new values, not just ids.
- Every mutating endpoint has a test asserting the resulting activity row. A
  removed `record_activity` call must break a test.

## TypeScript and React

- Strict TypeScript; `tsc --noEmit` is part of `make check`. `any` is a review
  failure; use `unknown` and narrow.
- Server state through TanStack Query hooks in `src/api/hooks`. Components do not
  call `fetch` directly.
- One component per file, named exports, no default exports except route entries.
- shadcn/ui components are owned source: edit them in place, never wrap them in a
  second abstraction.
- Every screen must work at 360px wide. Run Mode additionally works at projector
  size and from the keyboard.
- Loading, empty and error states are part of the component, not an afterthought.

## Tests

- Domain rules are unit-tested with no database and no HTTP.
- One integration test per entity asserting that mutations write activity.
- Tenancy and permission tests are generated from the matrices so a new capability
  without a test fails the suite.
- Tests are named for the rule they protect, not the function they call.

## Commits

- One logical change per commit, imperative subject, body explaining why.
- `make check` passes before the commit.
- Migrations and the model changes they support ship together.

## UX

- **If a user needs to understand the domain model to know which button to
  press, the UX has failed.** Say "Who's doing this?", not "Assign task owner".
- Every screen answers: what am I doing, what just happened, what do I do next.
- No technical error text in front of a user. Human sentence on screen, code in
  the logs.
- Never communicate a state with colour alone. Pair it with an icon or a word.
- Nothing is displayed that the system does not actually store.
- [17-ux.md](17-ux.md) is the full reference for voice, spacing and the game
  lifecycle.
