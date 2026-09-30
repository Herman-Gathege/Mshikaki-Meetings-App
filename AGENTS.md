# Mshikaki - working agreements

Read this before changing anything. It is short on purpose. The product reasoning
behind each rule lives in `docs/`, and `docs/standards.md` covers style.

## The invariants (non-negotiable)

1. **Every mutation writes an activity record** through
   `app.services.activity.record_activity`. Never insert activity rows anywhere
   else. A change without an activity row is a bug.
2. **Activity, xp_events and achievement_awards are append-only.** The application
   database role has `INSERT` and `SELECT` only. No code path updates or deletes
   them.
3. **Everything is team-scoped.** Every domain table carries `team_id`, and every
   query filters by the acting user's team. Cross-team reads return 404, never
   403.
4. **A task may be unowned only in `backlog`.** Any other status requires an owner.
5. **A task in `blocked` must have an open blocker.** The two can never disagree.
6. **XP is a ledger, never a stored total.** Awards are idempotent; corrections are
   new negative events with a reason.
7. **Deletion is soft and audited.** `deleted_at` plus an activity row holding a
   snapshot. Hard delete is admin-only.
8. **Origin links are permanent.** A task keeps its `session_id`, `idea_id` and
   `decision_id` forever, even when the source is deleted.
9. **Domain logic lives in `app/domain/` and stays pure.** No FastAPI, no
   SQLAlchemy, no I/O. `tests/unit/test_domain_purity.py` enforces it.
10. **Guests are people.** They can be participants, players and collaborators,
    but cannot log in until they claim a profile.

## Working agreements

- Read `docs/03-domain-model.md` and `docs/08-audit-trail.md` before changing the
  schema or adding an entity.
- The out-of-scope table in `docs/02-mvp-scope.md` is a contract. New scope enters
  only by removing scope, recorded in `docs/12-decision-log.md`.
- Use `task`, never "action". Use `session` for meetings and `auth_session` for
  logins.
- Permissions are checked in one place: `require_capability` in `app/deps.py`, or
  `can()` from `app/domain/permissions.py`. No `if role == ...` in a router.
- Routers do not contain business rules; services orchestrate; the domain decides.
- Every new endpoint that mutates gets a test asserting its activity row.
- Mobile-first at 360px. Run Mode is the one screen-first exception.
- No new dependency without a one-line rationale in the pull request.
- `make check` must pass before anything is considered done.
