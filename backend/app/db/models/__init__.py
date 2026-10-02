"""SQLAlchemy models.

Every model module is imported here so Alembic autogenerate sees the whole schema
through `Base.metadata`, and so importing `app.db.models` is enough to register
everything.
"""

from app.db.models.bragging import (
    Achievement,
    AchievementAward,
    Notification,
    Season,
    XpEvent,
    XpRuleModel,
)
from app.db.models.games import (
    ContentPack,
    GameAnswer,
    GameDefinition,
    GamePlay,
    GameQuestion,
    GameScore,
)
from app.db.models.identity import (
    AuthSession,
    Guest,
    Invite,
    Membership,
    Organization,
    Team,
    User,
)
from app.db.models.meeting import AgendaItem, Session, SessionParticipant
from app.db.models.record import Activity, Comment, Note
from app.db.models.work import (
    Blocker,
    Decision,
    Idea,
    IdeaTag,
    Project,
    Task,
    TaskCollaborator,
)

__all__ = [
    "Achievement",
    "AchievementAward",
    "Activity",
    "AgendaItem",
    "AuthSession",
    "Blocker",
    "Comment",
    "ContentPack",
    "Decision",
    "GameAnswer",
    "GameDefinition",
    "GamePlay",
    "GameQuestion",
    "GameScore",
    "Guest",
    "Idea",
    "IdeaTag",
    "Invite",
    "Membership",
    "Notification",
    "Note",
    "Organization",
    "Project",
    "Season",
    "Session",
    "SessionParticipant",
    "Task",
    "TaskCollaborator",
    "Team",
    "User",
    "XpEvent",
    "XpRuleModel",
]
