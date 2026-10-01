# Permissions

## Roles

| Role | Meaning |
|---|---|
| `owner` | created the team; organisation settings and deleting the team |
| `admin` | manages members, roles, content and XP rules |
| `facilitator` | runs sessions; elevated powers apply only inside sessions they facilitate |
| `member` | normal participant: capture, comment, own tasks, play |
| `guest` | a session-scoped identity with no account. Mshikaki no longer creates guests on join: scanning the invite makes a real member |

## How a decision is made

One place: `backend/app/domain/permissions.py`.

```python
can(actor, "task.status.any", Resource(team_id=..., owner_id=..., session_facilitator_id=...))
```

The capability table is pure data plus one-line predicates, so the whole matrix is
testable without a database. Routers use `require_capability("...")` for
team-level checks and `ensure_can(...)` when they have already loaded the target.

**No router branches on a role.** If you find yourself writing `if role ==`, the
capability you want is missing from the matrix.

## The rules worth remembering

- **Authorship beats hierarchy for content.** A member can always edit their own
  idea. An admin edits with attribution rather than silently rewriting history.
- **Facilitator power is session-scoped** and expires when the session closes.
- **Cross-team reads return 404, not 403.** Another team's session does not exist
  as far as you are concerned, which is both safer and simpler to test.
- **Refusals are recorded** as `permission.denied`, visible to admins.
- **UX never weakens this.** A friendlier flow still runs through `can`.

## Adding a capability

1. Add one row to `RULES` in `permissions.py`.
2. Add a case to the matrix test in `backend/tests/unit/test_permissions.py`.
3. Use it in a router or service.
4. Add an integration test for the role that should be refused.

The suite fails if a capability exists without a test, which is the point.

## What is tested

- Every capability for every role, including denials, generated from the matrix.
- Tenancy isolation: a second team cannot see or touch the first team's data.
- CSRF: a write without the required header is refused.
- Facilitator scoping, guest limitations and the owner-only actions.
