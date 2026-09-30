"""Statuses, roles and other closed vocabularies.

Plain `str` mixins rather than `StrEnum`, so the project keeps working on the
oldest Python we support. Always persist `.value`, never the enum's repr.
"""

from __future__ import annotations

from enum import Enum


class SessionStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ParticipantRole(str, Enum):
    FACILITATOR = "facilitator"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class IdeaStatus(str, Enum):
    NEW = "new"
    DISCUSSING = "discussing"
    ACCEPTED = "accepted"
    PARKED = "parked"
    REJECTED = "rejected"
    CONVERTED = "converted"


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"


class GameFamily(str, Enum):
    PROMPT_DECK = "prompt_deck"
    HOST_QUIZ = "host_quiz"
    HOST_SCORED = "host_scored"


class GamePlayStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class SeasonStatus(str, Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    CLOSED = "closed"


class TeamRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    FACILITATOR = "facilitator"
    MEMBER = "member"
    # Guests are not team members. The role exists so an Actor always has one.
    GUEST = "guest"


class MembershipStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ActorType(str, Enum):
    USER = "user"
    GUEST = "guest"
    SYSTEM = "system"


class CommentTarget(str, Enum):
    IDEA = "idea"
    DECISION = "decision"
    TASK = "task"
    BLOCKER = "blocker"
    SESSION = "session"


class ActivityVisibility(str, Enum):
    TEAM = "team"
    PARTICIPANTS = "participants"
    ADMIN = "admin"


SESSION_STATUSES = {s.value for s in SessionStatus}
IDEA_STATUSES = {s.value for s in IdeaStatus}
TASK_STATUSES = {s.value for s in TaskStatus}
TASK_PRIORITIES = {s.value for s in TaskPriority}
PROJECT_STATUSES = {s.value for s in ProjectStatus}
GAME_FAMILIES = {s.value for s in GameFamily}
GAME_PLAY_STATUSES = {s.value for s in GamePlayStatus}
TEAM_ROLES = {r.value for r in TeamRole}
MEMBERSHIP_STATUSES = {s.value for s in MembershipStatus}
COMMENT_TARGETS = {c.value for c in CommentTarget}
