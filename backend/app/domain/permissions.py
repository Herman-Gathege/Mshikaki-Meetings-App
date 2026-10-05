"""Who may do what.

Pure data plus pure predicates, so the whole capability matrix is testable without
a database. Routers call `can()` through `require_capability`; nothing else is
allowed to branch on a role.

Two ideas keep this simple:

* **Resource** carries only the context a decision needs (who owns the thing, who
  facilitates the session it belongs to). It is not a domain entity.
* **Rules are one-line predicates** in a table, so adding a capability means adding
  one row and one test case.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import SessionStatus, TeamRole


class UnknownCapability(Exception):
    """Raised when code asks about a capability that does not exist."""


@dataclass(frozen=True)
class Actor:
    """Who is acting. `guest_id` is set instead of `user_id` for guests."""

    role: str
    team_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None

    @property
    def is_guest(self) -> bool:
        return self.guest_id is not None and self.user_id is None

    @property
    def is_staff(self) -> bool:
        return self.role in {TeamRole.OWNER.value, TeamRole.ADMIN.value}

    @property
    def is_facilitator(self) -> bool:
        return self.role == TeamRole.FACILITATOR.value

    def owns(self, owner_id: uuid.UUID | None) -> bool:
        return owner_id is not None and owner_id == self.user_id

    def in_team(self, team_id: uuid.UUID | None) -> bool:
        return team_id is not None and team_id == self.team_id


@dataclass(frozen=True)
class Resource:
    """Context about the thing being acted on."""

    team_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    session_facilitator_id: uuid.UUID | None = None
    session_status: str | None = None
    collaborator_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)

    def session_is_open(self) -> bool:
        return self.session_status in {
            SessionStatus.ACTIVE.value,
            SessionStatus.PAUSED.value,
        }


EMPTY = Resource()

# Roles that can do the ordinary things.
_TEAM_ROLES = frozenset(
    {TeamRole.OWNER.value, TeamRole.ADMIN.value, TeamRole.FACILITATOR.value, TeamRole.MEMBER.value}
)
_STAFF = frozenset({TeamRole.OWNER.value, TeamRole.ADMIN.value})
_OWNER = frozenset({TeamRole.OWNER.value})
_RUNS_SESSIONS = frozenset({TeamRole.OWNER.value, TeamRole.ADMIN.value, TeamRole.FACILITATOR.value})


def _role_in(actor: Actor, roles: frozenset[str]) -> bool:
    return actor.role in roles


def _facilitates(actor: Actor, resource: Resource) -> bool:
    return (
        resource.session_facilitator_id is not None
        and actor.user_id is not None
        and resource.session_facilitator_id == actor.user_id
    )


def _manages_session(actor: Actor, resource: Resource) -> bool:
    """Staff, or the facilitator of this particular session."""
    return actor.is_staff or _facilitates(actor, resource)


def _owns_or_staff(actor: Actor, resource: Resource) -> bool:
    return actor.is_staff or actor.owns(resource.owner_id)


def _owns_or_manages(actor: Actor, resource: Resource) -> bool:
    return _manages_session(actor, resource) or actor.owns(resource.owner_id)


def _is_collaborator(actor: Actor, resource: Resource) -> bool:
    return actor.user_id is not None and actor.user_id in resource.collaborator_ids


# capability -> predicate. One row per capability; every row has a test.
RULES: dict[str, Callable[[Actor, Resource], bool]] = {
    # Team and membership
    "team.view": lambda a, r: _role_in(a, _TEAM_ROLES) or a.is_guest,
    "team.manage_members": lambda a, r: _role_in(a, _STAFF),
    "team.manage_settings": lambda a, r: _role_in(a, _OWNER),
    "invite.create": lambda a, r: _role_in(a, _STAFF),
    # Sessions
    "session.create": lambda a, r: _role_in(a, _TEAM_ROLES),
    "session.start.own": lambda a, r: _role_in(a, _TEAM_ROLES),
    "session.start.any": lambda a, r: _role_in(a, _STAFF),
    "session.close.own": lambda a, r: _role_in(a, _TEAM_ROLES),
    "session.close.any": lambda a, r: _role_in(a, _STAFF),
    "session.participant.manage": lambda a, r: _manages_session(a, r),
    # Joining a meeting you were invited to is not managing it: a team member
    # adds themselves while the room is open, and nobody has to create a second
    # account to be counted as present.
    "session.join.self": lambda a, r: (
        (_role_in(a, _TEAM_ROLES) or a.is_guest) and r.session_is_open()
    ),
    "agenda.manage": lambda a, r: _manages_session(a, r),
    # Notes are the room's scratchpad, so anybody in the meeting may add one.
    "note.create": lambda a, r: (_role_in(a, _TEAM_ROLES) or a.is_guest) and r.session_is_open(),
    "note.delete.any": lambda a, r: _manages_session(a, r),
    # Ideas
    "idea.create": lambda a, r: _role_in(a, _TEAM_ROLES),
    "idea.create.as_guest": lambda a, r: a.is_guest and r.session_is_open(),
    "idea.edit.own": lambda a, r: _role_in(a, _TEAM_ROLES) and a.owns(r.owner_id),
    "idea.edit.as_guest": lambda a, r: a.is_guest and r.session_is_open(),
    "idea.edit.any": lambda a, r: _manages_session(a, r),
    "idea.delete.any": lambda a, r: _role_in(a, _STAFF),
    "idea.convert": lambda a, r: _role_in(a, _TEAM_ROLES),
    # Decisions
    "decision.record": lambda a, r: _role_in(a, _TEAM_ROLES),
    "decision.edit.any": lambda a, r: _manages_session(a, r),
    "decision.delete.any": lambda a, r: _role_in(a, _STAFF),
    # Tasks
    "task.create": lambda a, r: _role_in(a, _TEAM_ROLES),
    "task.assign.other": lambda a, r: _role_in(a, _RUNS_SESSIONS),
    "task.assign.self": lambda a, r: _role_in(a, _TEAM_ROLES),
    "task.edit.own": lambda a, r: _role_in(a, _TEAM_ROLES) and a.owns(r.owner_id),
    "task.edit.any": lambda a, r: _role_in(a, _RUNS_SESSIONS) or _is_collaborator(a, r),
    "task.status.own": lambda a, r: (
        _role_in(a, _TEAM_ROLES) and (a.owns(r.owner_id) or _is_collaborator(a, r))
    ),
    "task.status.any": lambda a, r: _manages_session(a, r),
    "task.delete.any": lambda a, r: _role_in(a, _STAFF),
    # Blockers
    "blocker.raise": lambda a, r: _role_in(a, _TEAM_ROLES),
    "blocker.resolve": lambda a, r: _owns_or_manages(a, r) or _is_collaborator(a, r),
    # Comments
    "comment.create": lambda a, r: _role_in(a, _TEAM_ROLES) or (a.is_guest and r.session_is_open()),
    "comment.delete.own": lambda a, r: a.owns(r.owner_id),
    "comment.delete.any": lambda a, r: _role_in(a, _STAFF),
    # Projects
    "project.create": lambda a, r: _role_in(a, _RUNS_SESSIONS),
    "project.manage": lambda a, r: _role_in(a, _RUNS_SESSIONS) or a.owns(r.owner_id),
    # Games
    "game.launch": lambda a, r: _role_in(a, _RUNS_SESSIONS),
    # Playing is the whole point of a session, so members and guests may answer;
    # anybody can still be scored by the host without answering.
    "game.answer": lambda a, r: (_role_in(a, _TEAM_ROLES) or a.is_guest) and r.session_is_open(),
    "game.score": lambda a, r: _manages_session(a, r),
    "game.score.override": lambda a, r: _manages_session(a, r),
    "content.manage": lambda a, r: _role_in(a, _STAFF),
    # XP and bragging rights
    "xp.rule.manage": lambda a, r: _role_in(a, _STAFF),
    "achievement.revoke": lambda a, r: _role_in(a, _STAFF),
    "leaderboard.view": lambda a, r: True,
    # Record and reporting
    "activity.view.team": lambda a, r: _role_in(a, _TEAM_ROLES),
    "activity.view.admin": lambda a, r: _role_in(a, _STAFF),
    "metrics.view": lambda a, r: _role_in(a, _TEAM_ROLES),
    "search.use": lambda a, r: _role_in(a, _TEAM_ROLES),
}

CAPABILITIES: frozenset[str] = frozenset(RULES)


def can(actor: Actor, capability: str, resource: Resource | None = None) -> bool:
    """The single entry point for every permission decision."""
    rule = RULES.get(capability)
    if rule is None:
        raise UnknownCapability(f"Unknown capability: {capability}")

    resource = resource or EMPTY
    if not actor.is_guest and not actor.in_team(resource.team_id) and resource.team_id is not None:
        # A user from another team never has power here, whatever their role.
        return False
    return rule(actor, resource)


def explain(actor: Actor, capability: str, resource: Resource | None = None) -> dict[str, Any]:
    """Debug helper: why was this allowed or denied? Not used in request paths."""
    allowed = can(actor, capability, resource)
    return {
        "capability": capability,
        "allowed": allowed,
        "role": actor.role,
        "is_guest": actor.is_guest,
    }
