"""The capability matrix, exercised cell by cell.

Every authorization decision in Mshikaki goes through `can()`. If a capability
is added without a case here the suite fails, so the matrix cannot quietly grow
an untested rule.
"""

from __future__ import annotations

import uuid

import pytest
from app.domain.enums import TeamRole
from app.domain.permissions import RULES, Actor, Resource, UnknownCapability, can

TEAM = uuid.uuid4()
OTHER_TEAM = uuid.uuid4()
OWNER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
FACILITATOR_ID = uuid.uuid4()
MEMBER_ID = uuid.uuid4()
OTHER_MEMBER_ID = uuid.uuid4()
GUEST_ID = uuid.uuid4()

OWNER = Actor(role=TeamRole.OWNER.value, team_id=TEAM, user_id=OWNER_ID)
ADMIN = Actor(role=TeamRole.ADMIN.value, team_id=TEAM, user_id=ADMIN_ID)
FACILITATOR = Actor(role=TeamRole.FACILITATOR.value, team_id=TEAM, user_id=FACILITATOR_ID)
MEMBER = Actor(role=TeamRole.MEMBER.value, team_id=TEAM, user_id=MEMBER_ID)
OTHER_MEMBER = Actor(role=TeamRole.MEMBER.value, team_id=TEAM, user_id=OTHER_MEMBER_ID)
GUEST = Actor(role=TeamRole.GUEST.value, team_id=TEAM, guest_id=GUEST_ID)
STRANGER = Actor(role=TeamRole.OWNER.value, team_id=OTHER_TEAM, user_id=uuid.uuid4())

# Resources: the same objects seen from different people's point of view.
OPEN_SESSION_MINE = Resource(
    team_id=TEAM, session_facilitator_id=FACILITATOR_ID, session_status="active"
)
OPEN_SESSION_OTHERS = Resource(
    team_id=TEAM, session_facilitator_id=OTHER_MEMBER_ID, session_status="active"
)
CLOSED_SESSION = Resource(
    team_id=TEAM, session_facilitator_id=FACILITATOR_ID, session_status="completed"
)
MY_IDEA = Resource(team_id=TEAM, owner_id=MEMBER_ID, session_facilitator_id=FACILITATOR_ID)
OTHER_IDEA = Resource(team_id=TEAM, owner_id=OTHER_MEMBER_ID, session_facilitator_id=FACILITATOR_ID)
MY_TASK = Resource(team_id=TEAM, owner_id=MEMBER_ID, session_facilitator_id=FACILITATOR_ID)
MY_TASK_IN_MY_SESSION = Resource(
    team_id=TEAM, owner_id=MEMBER_ID, session_facilitator_id=FACILITATOR_ID
)
COLLEAGUE_TASK = Resource(
    team_id=TEAM,
    owner_id=OTHER_MEMBER_ID,
    session_facilitator_id=FACILITATOR_ID,
    collaborator_ids=frozenset({MEMBER_ID}),
)
UNRELATED_TASK = Resource(
    team_id=TEAM, owner_id=OTHER_MEMBER_ID, session_facilitator_id=FACILITATOR_ID
)
PLAIN = Resource(team_id=TEAM)
FOREIGN = Resource(team_id=OTHER_TEAM, owner_id=MEMBER_ID)

# (capability, actor, resource, expected)
CASES: list[tuple[str, Actor, Resource, bool]] = [
    # Team and access
    ("team.view", MEMBER, PLAIN, True),
    ("team.view", GUEST, PLAIN, True),
    ("team.manage_members", ADMIN, PLAIN, True),
    ("team.manage_members", FACILITATOR, PLAIN, False),
    ("team.manage_settings", OWNER, PLAIN, True),
    ("team.manage_settings", ADMIN, PLAIN, False),
    ("invite.create", ADMIN, PLAIN, True),
    ("invite.create", MEMBER, PLAIN, False),
    # Sessions
    ("session.create", MEMBER, PLAIN, True),
    ("session.create", GUEST, PLAIN, False),
    ("session.start.own", MEMBER, PLAIN, True),
    ("session.start.any", ADMIN, PLAIN, True),
    ("session.start.any", FACILITATOR, PLAIN, False),
    ("session.close.own", MEMBER, PLAIN, True),
    ("session.close.any", ADMIN, PLAIN, True),
    ("session.participant.manage", FACILITATOR, OPEN_SESSION_MINE, True),
    ("session.participant.manage", FACILITATOR, OPEN_SESSION_OTHERS, False),
    ("session.participant.manage", MEMBER, PLAIN, False),
    ("agenda.manage", FACILITATOR, OPEN_SESSION_MINE, True),
    ("agenda.manage", MEMBER, PLAIN, False),
    # Ideas
    ("idea.create", MEMBER, PLAIN, True),
    ("idea.create", GUEST, PLAIN, False),
    ("idea.create.as_guest", GUEST, OPEN_SESSION_MINE, True),
    ("idea.create.as_guest", GUEST, CLOSED_SESSION, False),
    ("idea.edit.own", MEMBER, MY_IDEA, True),
    ("idea.edit.own", MEMBER, OTHER_IDEA, False),
    ("idea.edit.as_guest", GUEST, OPEN_SESSION_MINE, True),
    ("idea.edit.any", FACILITATOR, MY_IDEA, True),
    ("idea.edit.any", MEMBER, OTHER_IDEA, False),
    ("idea.delete.any", ADMIN, OTHER_IDEA, True),
    ("idea.delete.any", FACILITATOR, OTHER_IDEA, False),
    ("idea.convert", MEMBER, MY_IDEA, True),
    # Decisions
    ("decision.record", MEMBER, PLAIN, True),
    ("decision.edit.any", FACILITATOR, MY_IDEA, True),
    ("decision.edit.any", MEMBER, MY_IDEA, False),
    ("decision.delete.any", ADMIN, PLAIN, True),
    # Tasks
    ("task.create", MEMBER, PLAIN, True),
    ("task.assign.other", FACILITATOR, PLAIN, True),
    ("task.assign.other", MEMBER, PLAIN, False),
    ("task.assign.self", MEMBER, PLAIN, True),
    ("task.edit.own", MEMBER, MY_TASK, True),
    ("task.edit.any", FACILITATOR, MY_TASK_IN_MY_SESSION, True),
    ("task.edit.any", MEMBER, COLLEAGUE_TASK, True),
    ("task.edit.any", MEMBER, UNRELATED_TASK, False),
    ("task.status.own", MEMBER, MY_TASK, True),
    ("task.status.own", MEMBER, COLLEAGUE_TASK, True),
    ("task.status.own", MEMBER, UNRELATED_TASK, False),
    ("task.status.any", FACILITATOR, MY_TASK_IN_MY_SESSION, True),
    ("task.status.any", MEMBER, PLAIN, False),
    ("task.delete.any", ADMIN, PLAIN, True),
    ("task.delete.any", FACILITATOR, PLAIN, False),
    # Blockers
    ("blocker.raise", MEMBER, PLAIN, True),
    ("blocker.resolve", MEMBER, MY_TASK, True),
    ("blocker.resolve", MEMBER, COLLEAGUE_TASK, True),
    ("blocker.resolve", MEMBER, UNRELATED_TASK, False),
    ("blocker.resolve", ADMIN, UNRELATED_TASK, True),
    # Comments
    ("comment.create", MEMBER, PLAIN, True),
    ("comment.create", GUEST, OPEN_SESSION_MINE, True),
    ("comment.create", GUEST, CLOSED_SESSION, False),
    ("comment.delete.own", MEMBER, MY_IDEA, True),
    ("comment.delete.own", MEMBER, OTHER_IDEA, False),
    ("comment.delete.any", ADMIN, OTHER_IDEA, True),
    # Projects
    ("project.create", FACILITATOR, PLAIN, True),
    ("project.create", MEMBER, PLAIN, False),
    ("project.manage", FACILITATOR, PLAIN, True),
    # Games
    ("game.launch", FACILITATOR, PLAIN, True),
    ("game.launch", MEMBER, PLAIN, False),
    # Notes are the room's scratchpad while the meeting runs.
    ("note.create", MEMBER, OPEN_SESSION_MINE, True),
    ("note.create", GUEST, OPEN_SESSION_MINE, True),
    ("note.create", MEMBER, CLOSED_SESSION, False),
    ("note.delete.any", FACILITATOR, OPEN_SESSION_MINE, True),
    ("note.delete.any", MEMBER, OPEN_SESSION_MINE, False),
    # Questions the room writes during the meeting.
    ("question.suggest", MEMBER, OPEN_SESSION_MINE, True),
    ("question.suggest", GUEST, OPEN_SESSION_MINE, True),
    ("question.suggest", MEMBER, CLOSED_SESSION, False),
    ("question.manage", FACILITATOR, OPEN_SESSION_MINE, True),
    ("question.manage", MEMBER, OPEN_SESSION_MINE, False),
    # Anybody in the team may put themselves in a meeting that is running.
    ("session.join.self", MEMBER, OPEN_SESSION_MINE, True),
    ("session.join.self", FACILITATOR, OPEN_SESSION_MINE, True),
    ("session.join.self", MEMBER, CLOSED_SESSION, False),
    ("session.join.self", STRANGER, OPEN_SESSION_MINE, False),
    # Playing is open to the room while the meeting runs, and only then.
    ("game.answer", MEMBER, OPEN_SESSION_MINE, True),
    ("game.answer", GUEST, OPEN_SESSION_MINE, True),
    ("game.answer", MEMBER, CLOSED_SESSION, False),
    ("game.answer", STRANGER, OPEN_SESSION_MINE, False),
    ("game.score", FACILITATOR, OPEN_SESSION_MINE, True),
    ("game.score", MEMBER, OPEN_SESSION_MINE, False),
    ("game.score.override", FACILITATOR, OPEN_SESSION_MINE, True),
    ("content.manage", ADMIN, PLAIN, True),
    ("content.manage", FACILITATOR, PLAIN, False),
    # Bragging rights
    ("xp.rule.manage", ADMIN, PLAIN, True),
    ("xp.rule.manage", MEMBER, PLAIN, False),
    ("achievement.revoke", ADMIN, PLAIN, True),
    ("leaderboard.view", GUEST, PLAIN, True),
    ("leaderboard.view", MEMBER, PLAIN, True),
    # Record
    ("activity.view.team", MEMBER, PLAIN, True),
    ("activity.view.team", GUEST, PLAIN, False),
    ("activity.view.admin", ADMIN, PLAIN, True),
    ("activity.view.admin", MEMBER, PLAIN, False),
    ("metrics.view", MEMBER, PLAIN, True),
    ("search.use", MEMBER, PLAIN, True),
]


@pytest.mark.parametrize(
    ("capability", "actor", "resource", "expected"),
    CASES,
    ids=[f"{capability}:{actor.role}:{expected}" for capability, actor, _, expected in CASES],
)
def test_capability(capability: str, actor: Actor, resource: Resource, expected: bool) -> None:
    assert can(actor, capability, resource) is expected


def test_every_capability_has_a_case() -> None:
    """Adding a capability without a test fails here, which is the point."""
    covered = {capability for capability, *_ in CASES}
    assert set(RULES) - covered == set(), "capabilities without a test case"


def test_another_team_is_never_allowed() -> None:
    """Cross-team access is refused before any role rule is considered."""
    # STRANGER is a legitimate owner, of a different team, touching this team's
    # resources. Their role must not buy them anything here.
    for capability in RULES:
        assert can(STRANGER, capability, PLAIN) is False, capability


def test_guests_cannot_administer_anything() -> None:
    administrative = [
        "team.manage_members",
        "team.manage_settings",
        "invite.create",
        "idea.delete.any",
        "task.delete.any",
        "content.manage",
        "xp.rule.manage",
        "achievement.revoke",
        "activity.view.admin",
        "game.launch",
        "project.create",
    ]
    for capability in administrative:
        assert can(GUEST, capability, OPEN_SESSION_MINE) is False, capability


def test_unknown_capability_is_a_programming_error() -> None:
    with pytest.raises(UnknownCapability):
        can(MEMBER, "task.teleport", PLAIN)
