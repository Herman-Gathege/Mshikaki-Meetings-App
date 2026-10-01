"""Request and response shapes.

Requests are validated here; responses are plain dictionaries built by the service
layer, because a response shape that mirrors the database exactly is not a
contract worth maintaining twice.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    team_name: str | None = Field(default=None, max_length=200)
    invite_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class JoinRequest(BaseModel):
    code: str = Field(min_length=4, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    timezone: str | None = Field(default=None, max_length=64)


class InviteRequest(BaseModel):
    email: EmailStr | None = None
    role: str = "member"


class RoleChangeRequest(BaseModel):
    role: str


class GuestRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None


class ClaimGuestRequest(BaseModel):
    user_id: uuid.UUID


class SessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    scheduled_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    agenda: list[str] = Field(default_factory=list)
    facilitator_id: uuid.UUID | None = None


class SessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    scheduled_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)


class ReopenRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class CancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class RunModeStageRequest(BaseModel):
    stage: str = Field(min_length=2, max_length=16)


class ParticipantRequest(BaseModel):
    user_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None
    role: str = "participant"


class AttendanceRequest(BaseModel):
    attended: bool


class AgendaRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    timebox_minutes: int | None = Field(default=None, ge=1, le=180)


class IdeaCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    session_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)


class IdeaUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: str | None = None
    tags: list[str] | None = None


class DecisionCreateRequest(BaseModel):
    statement: str = Field(min_length=3, max_length=2000)
    session_id: uuid.UUID | None = None
    idea_id: uuid.UUID | None = None
    rationale: str | None = None
    standalone_reason: str | None = None


class DecisionSupersedeRequest(BaseModel):
    statement: str = Field(min_length=3, max_length=2000)
    rationale: str | None = None


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    owner_id: uuid.UUID | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: str | None = None


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    owner_id: uuid.UUID | None = None
    status: str = "backlog"
    priority: str = "normal"
    due_date: date | None = None
    project_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    idea_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    collaborator_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    priority: str | None = None
    due_date: date | None = None
    project_id: uuid.UUID | None = None


class TaskAssignRequest(BaseModel):
    owner_id: uuid.UUID | None = None


class TaskStatusRequest(BaseModel):
    status: str
    reason: str | None = Field(default=None, max_length=300)


class CollaboratorRequest(BaseModel):
    user_id: uuid.UUID


class BlockerCreateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class BlockerResolveRequest(BaseModel):
    resolution: str = Field(min_length=2, max_length=1000)


class CommentCreateRequest(BaseModel):
    target_type: str
    target_id: uuid.UUID
    body: str = Field(min_length=1, max_length=4000)


class PlayCreateRequest(BaseModel):
    game_key: str
    content_pack_id: uuid.UUID | None = None
    settings: dict = Field(default_factory=dict)


class ScoreAwardRequest(BaseModel):
    user_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None
    points: int = Field(default=10, ge=-100, le=100)
    correct: bool = True


class AnswerRequest(BaseModel):
    """One player's own answer while the question is live."""

    choice: str = Field(min_length=1, max_length=300)


class ScoreOverrideRequest(BaseModel):
    user_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None
    points: int = Field(ge=0, le=10000)
    reason: str = Field(min_length=3, max_length=300)


class PreferencesRequest(BaseModel):
    leaderboard_opt_out: bool | None = None
    display_name: str | None = Field(default=None, max_length=120)


class IdeaConvertRequest(BaseModel):
    target_type: str
    target_id: uuid.UUID
