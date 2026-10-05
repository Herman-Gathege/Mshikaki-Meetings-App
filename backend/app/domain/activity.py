"""The audit trail's vocabulary.

Two jobs:

1. **The whitelist.** Only verbs in `VERBS` may be written. An unknown verb raises,
   which turns a typo into a test failure instead of an unreadable history.
2. **The sentence.** `describe()` renders any record the same way everywhere, so
   the session view, the team feed and an entity's history all read alike.

Deliberately absent: page views, searches, keystrokes, presence, notification
reads. The trail records what happened to the work, not what people looked at.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import ActivityVisibility


class UnknownVerb(Exception):
    """Raised when code tries to record an activity that is not whitelisted."""


@dataclass(frozen=True)
class VerbSpec:
    key: str
    template: str
    visibility: str = ActivityVisibility.TEAM.value
    # XP rule key this verb can feed, if any. The XP service decides amounts.
    xp_rule: str | None = None


V = VerbSpec

VERBS: dict[str, VerbSpec] = {
    # Sessions
    "session.created": V("session.created", 'created the session "{title}"'),
    "session.updated": V("session.updated", "updated the session details"),
    "session.started": V("session.started", "started the session"),
    "session.paused": V("session.paused", "paused the session"),
    "session.resumed": V("session.resumed", "resumed the session"),
    "session.closed": V(
        "session.closed",
        "closed the session: {ideas} idea(s), {decisions} decision(s), {tasks} task(s)",
    ),
    "session.reopened": V("session.reopened", "reopened the session: {reason}"),
    "session.cancelled": V("session.cancelled", "cancelled the meeting: {reason}"),
    "session.participant_joined": V(
        "session.participant_joined", "joined the session as {role}", xp_rule="attend_session"
    ),
    "session.participant_removed": V(
        "session.participant_removed", "removed {name} from the session"
    ),
    "session.attendance_changed": V("session.attendance_changed", "marked {name} as {attended}"),
    "agenda.added": V("agenda.added", 'added "{title}" to the agenda'),
    "agenda.updated": V("agenda.updated", 'changed the agenda item "{title}"'),
    "agenda.covered": V("agenda.covered", 'covered the agenda item "{title}"'),
    "agenda.outcome": V(
        "agenda.outcome",
        'closed "{title}" as {outcome}',
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    "agenda.removed": V("agenda.removed", 'removed the agenda item "{title}"'),
    "meeting.started": V(
        "meeting.started",
        "took the room into the meeting",
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    "note.added": V(
        "note.added",
        "noted: {body}",
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    "note.updated": V(
        "note.updated",
        "changed a note ({changes})",
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    "note.removed": V("note.removed", "removed a note"),
    # Games
    "game.started": V(
        "game.started", 'started "{game}"', visibility=ActivityVisibility.PARTICIPANTS.value
    ),
    "game.finished": V(
        "game.finished",
        'finished "{game}" - {winner} won',
        visibility=ActivityVisibility.PARTICIPANTS.value,
        xp_rule="game_played",
    ),
    "game.abandoned": V("game.abandoned", 'stopped "{game}" early'),
    "game.answer_revealed": V(
        "game.answer_revealed",
        'revealed the answer to "{question}" in {game}',
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    "game.point_awarded": V(
        "game.point_awarded",
        "awarded {points} to {player} in {game}",
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    "game.score_adjusted": V(
        "game.score_adjusted",
        "changed {player}'s score from {old} to {new}: {reason}",
        visibility=ActivityVisibility.PARTICIPANTS.value,
    ),
    # Ideas
    "idea.created": V("idea.created", 'captured the idea "{title}"', xp_rule="idea_submitted"),
    "idea.updated": V("idea.updated", 'edited the idea "{title}"'),
    "idea.status_changed": V(
        "idea.status_changed",
        'moved the idea "{title}" from {old} to {new}',
        xp_rule="idea_accepted",
    ),
    "idea.converted": V("idea.converted", 'turned the idea "{title}" into {target_type}'),
    "idea.deleted": V("idea.deleted", 'deleted the idea "{title}"'),
    # Decisions
    "decision.recorded": V(
        "decision.recorded", 'recorded a decision: "{statement}"', xp_rule="decision_recorded"
    ),
    "decision.updated": V("decision.updated", 'edited the decision "{statement}"'),
    "decision.superseded": V("decision.superseded", 'superseded the decision "{statement}"'),
    "decision.deleted": V("decision.deleted", 'deleted the decision "{statement}"'),
    # Tasks
    "task.created": V("task.created", 'created the task "{title}"{owner_suffix}'),
    "task.updated": V("task.updated", 'edited the task "{title}"'),
    "task.assigned": V("task.assigned", 'assigned "{title}" to {new}'),
    "task.status_changed": V(
        "task.status_changed",
        'moved the task "{title}" from {old} to {new}',
        xp_rule="task_completed",
    ),
    "task.reopened": V("task.reopened", 'reopened the task "{title}"'),
    "task.priority_changed": V("task.priority_changed", 'set "{title}" priority to {new}'),
    "task.due_date_changed": V("task.due_date_changed", 'moved "{title}" due date to {new}'),
    "task.deleted": V("task.deleted", 'deleted the task "{title}"'),
    "task.collaborator_added": V("task.collaborator_added", 'added {name} to "{title}"'),
    "task.collaborator_removed": V("task.collaborator_removed", 'removed {name} from "{title}"'),
    # Blockers
    "blocker.raised": V("blocker.raised", 'blocked "{title}": {reason}'),
    "blocker.resolved": V(
        "blocker.resolved", 'unblocked "{title}": {resolution}', xp_rule="blocker_resolved"
    ),
    # Comments
    "comment.created": V("comment.created", 'commented on {target_label}: "{excerpt}"'),
    "comment.updated": V("comment.updated", "edited a comment on {target_label}"),
    "comment.deleted": V("comment.deleted", "deleted a comment on {target_label}"),
    # Projects
    "project.created": V("project.created", 'created the project "{title}"'),
    "project.updated": V("project.updated", 'edited the project "{title}"'),
    "project.status_changed": V(
        "project.status_changed", 'moved the project "{title}" from {old} to {new}'
    ),
    # Team and access
    "member.joined": V("member.joined", "joined the team as {role}"),
    "member.role_changed": V(
        "member.role_changed",
        "changed {name}'s role from {old} to {new}",
        visibility=ActivityVisibility.ADMIN.value,
    ),
    "member.removed": V(
        "member.removed", "removed {name} from the team", visibility=ActivityVisibility.ADMIN.value
    ),
    "invite.created": V(
        "invite.created", "invited {name} as {role}", visibility=ActivityVisibility.ADMIN.value
    ),
    "guest.created": V("guest.created", "added {name} as a guest"),
    "guest.claimed": V("guest.claimed", "linked the guest {name} to a profile"),
    "permission.denied": V(
        "permission.denied", "was denied {action}", visibility=ActivityVisibility.ADMIN.value
    ),
    # Bragging rights
    "xp.awarded": V("xp.awarded", "earned {amount} XP for {reason}"),
    "xp.reversed": V(
        "xp.reversed",
        "had {amount} XP reversed: {reason}",
        visibility=ActivityVisibility.ADMIN.value,
    ),
    "achievement.awarded": V("achievement.awarded", "unlocked {achievement} {emoji}"),
    "achievement.revoked": V(
        "achievement.revoked",
        "lost {achievement}: {reason}",
        visibility=ActivityVisibility.ADMIN.value,
    ),
}

VERB_KEYS: frozenset[str] = frozenset(VERBS)


class _SafePayload(dict):
    """Missing placeholders render as an em dash instead of raising.

    A malformed payload must never break the write that produced it: an ugly
    sentence is a bug to fix, a lost audit row is data loss.
    """

    def __missing__(self, key: str) -> str:
        return "-"


def spec(verb: str) -> VerbSpec:
    try:
        return VERBS[verb]
    except KeyError as exc:  # pragma: no cover - guarded by tests
        raise UnknownVerb(f"'{verb}' is not a whitelisted activity verb") from exc


def describe(verb: str, payload: dict[str, Any] | None = None) -> str:
    """The action phrase, without the actor: 'created the task "Fix the mixer"'."""
    data = _SafePayload(payload or {})
    data.setdefault("title", "untitled")
    data.setdefault("statement", "untitled")
    data.setdefault("name", "someone")
    data.setdefault("reason", "no reason given")
    data.setdefault("resolution", "resolved")
    data.setdefault("excerpt", "...")
    data.setdefault("target_label", "an item")
    data.setdefault("target_type", "work")
    data.setdefault("game", "a game")
    data.setdefault("winner", "nobody")
    data.setdefault("player", "a player")
    data.setdefault("points", 0)
    data.setdefault("achievement", "an achievement")
    data.setdefault("emoji", "")
    data.setdefault("action", "an action")
    data.setdefault("amount", 0)
    data.setdefault("ideas", 0)
    data.setdefault("decisions", 0)
    data.setdefault("tasks", 0)
    if not data.get("owner_suffix"):
        owner = data.get("owner_name")
        data["owner_suffix"] = f" for {owner}" if owner else ""
    return spec(verb).template.format_map(data)


def full_sentence(actor_name: str | None, verb: str, payload: dict[str, Any] | None = None) -> str:
    """What the UI shows: 'Herman created the task "Fix the mixer"'."""
    who = actor_name or "Someone"
    return f"{who} {describe(verb, payload)}"


def xp_rule_for(verb: str) -> str | None:
    return spec(verb).xp_rule


def visibility_for(verb: str) -> str:
    return spec(verb).visibility
