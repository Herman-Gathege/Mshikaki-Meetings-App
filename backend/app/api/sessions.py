"""Sessions, participants, the agenda and the summary."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session as DbSession

from app.deps import ContextDep, DbDep, ensure_can, require_capability
from app.domain import minutes as minutes_domain
from app.domain.permissions import Resource, can
from app.errors import AppError, PermissionDeniedError
from app.schemas import (
    AgendaRequest,
    AttendanceRequest,
    CancelRequest,
    ParticipantRequest,
    ReopenRequest,
    RunModeStageRequest,
    SessionCreateRequest,
    SessionUpdateRequest,
)
from app.services import activity as activity_service
from app.services import meetings
from app.services import summary as summary_service

router = APIRouter(tags=["sessions"])


def session_resource(context, session) -> Resource:
    return Resource(
        team_id=context.team.id,
        session_id=session.id,
        session_facilitator_id=session.facilitator_id,
        session_status=session.status,
    )


def ensure_lifecycle(context, session, action: str) -> None:
    """Staff can act on any session; everyone else on the ones they facilitate."""
    resource = session_resource(context, session)
    is_staff = can(context.actor, f"session.{action}.any", resource)
    is_facilitator = session.facilitator_id == context.actor.user_id
    if is_staff or (is_facilitator and can(context.actor, f"session.{action}.own", resource)):
        return
    raise PermissionDeniedError("Only the facilitator or an admin can do that here.")


@router.get("/sessions")
def list_sessions(context=ContextDep, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    items = meetings.list_sessions(db, team_id=context.team.id)
    return {"items": items, "total": len(items)}


@router.post("/sessions")
def create_session(
    payload: SessionCreateRequest,
    context=require_capability("session.create"),
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.create_session(
        db,
        team_id=context.team.id,
        team_name=context.team.name,
        actor=context.actor,
        actor_name=context.name,
        title=payload.title,
        scheduled_at=payload.scheduled_at,
        location=payload.location,
        agenda=payload.agenda,
        facilitator_id=payload.facilitator_id,
    )
    return meetings.session_detail(db, session)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    return meetings.session_detail(db, session)


@router.patch("/sessions/{session_id}")
def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdateRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "close")
    if payload.title is not None and payload.title.strip():
        session.title = payload.title.strip()[:200]
    if payload.scheduled_at is not None:
        session.scheduled_at = payload.scheduled_at
    if payload.location is not None:
        session.location = payload.location
    activity_service.record_activity(
        db,
        team_id=context.team.id,
        session_id=session.id,
        actor=context.actor,
        actor_name=context.name,
        verb="session.updated",
        target_type="session",
        target_id=session.id,
        payload={"title": session.title},
    )
    db.flush()
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/start")
def start_session(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "start")
    meetings.start_session(db, session=session, actor=context.actor, actor_name=context.name)
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/pause")
def pause_session(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "close")
    meetings.pause_session(db, session=session, actor=context.actor, actor_name=context.name)
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/resume")
def resume_session(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "start")
    meetings.resume_session(db, session=session, actor=context.actor, actor_name=context.name)
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/close")
def close_session(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "close")
    meetings.close_session(db, session=session, actor=context.actor, actor_name=context.name)
    _sync_achievements_for_session(db, session)
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/reopen")
def reopen_session(
    session_id: uuid.UUID,
    payload: ReopenRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "start")
    meetings.reopen_session(
        db, session=session, actor=context.actor, actor_name=context.name, reason=payload.reason
    )
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/cancel")
def cancel_session(
    session_id: uuid.UUID,
    payload: CancelRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    """A meeting that is not going to happen. Kept in the record, with the reason."""
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "close")
    meetings.cancel_session(
        db,
        session=session,
        actor=context.actor,
        actor_name=context.name,
        reason=payload.reason,
    )
    return meetings.session_detail(db, session)


@router.post("/sessions/{session_id}/run-mode")
def set_run_mode_stage(
    session_id: uuid.UUID,
    payload: RunModeStageRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    """The facilitator's current stage. Participants poll the session and follow.

    Deliberately not an activity record: moving the room from one screen to the
    next is navigation, not a change to the work, and recording every tap would
    drown the trail.
    """
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "start")
    meetings.set_run_mode_stage(
        db, session=session, stage=payload.stage, actor=context.actor, actor_name=context.name
    )
    return meetings.session_detail(db, session)


def _sync_achievements_for_session(db: DbSession, session) -> None:
    """Session close is the natural moment to settle the bragging rights."""
    from app.services.bragging import sync_achievements

    for participant in session.participants:
        if participant.user_id is not None:
            sync_achievements(db, team_id=session.team_id, user_id=participant.user_id)


@router.get("/sessions/{session_id}/participants")
def list_participants(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    items = meetings.participants(db, session)
    return {"items": items, "total": len(items)}


@router.post("/sessions/{session_id}/participants")
def add_participant(
    session_id: uuid.UUID,
    payload: ParticipantRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_can(context.actor, "session.participant.manage", session_resource(context, session))
    meetings.add_participant(
        db,
        session=session,
        actor=context.actor,
        actor_name=context.name,
        user_id=payload.user_id,
        guest_id=payload.guest_id,
        role=payload.role,
    )
    return {"items": meetings.participants(db, session)}


@router.patch("/sessions/{session_id}/participants/{participant_id}")
def mark_attendance(
    session_id: uuid.UUID,
    participant_id: uuid.UUID,
    payload: AttendanceRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_can(context.actor, "session.participant.manage", session_resource(context, session))
    meetings.mark_attendance(
        db,
        session=session,
        participant_id=participant_id,
        attended=payload.attended,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"items": meetings.participants(db, session)}


@router.delete("/sessions/{session_id}/participants/{participant_id}")
def remove_participant(
    session_id: uuid.UUID,
    participant_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_can(context.actor, "session.participant.manage", session_resource(context, session))
    meetings.remove_participant(
        db,
        session=session,
        participant_id=participant_id,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"items": meetings.participants(db, session)}


@router.get("/sessions/{session_id}/agenda")
def list_agenda(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    return {"items": meetings.session_detail(db, session)["agenda"]}


@router.post("/sessions/{session_id}/agenda")
def add_agenda_item(
    session_id: uuid.UUID,
    payload: AgendaRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_can(context.actor, "agenda.manage", session_resource(context, session))
    meetings.add_agenda_item(
        db,
        session=session,
        title=payload.title,
        timebox_minutes=payload.timebox_minutes,
        actor=context.actor,
        actor_name=context.name,
    )
    return {"items": meetings.session_detail(db, session)["agenda"]}


@router.post("/sessions/{session_id}/agenda/{item_id}/cover")
def cover_agenda_item(
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_can(context.actor, "agenda.manage", session_resource(context, session))
    meetings.cover_agenda_item(
        db, session=session, item_id=item_id, actor=context.actor, actor_name=context.name
    )
    return {"items": meetings.session_detail(db, session)["agenda"]}


@router.delete("/sessions/{session_id}/agenda/{item_id}")
def remove_agenda_item(
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_can(context.actor, "agenda.manage", session_resource(context, session))
    meetings.remove_agenda_item(
        db, session=session, item_id=item_id, actor=context.actor, actor_name=context.name
    )
    return {"items": meetings.session_detail(db, session)["agenda"]}


@router.get("/sessions/{session_id}/summary")
def get_summary(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    if session.summary_snapshot is None:
        return {"summary": None, "text": None, "generated_at": None}
    return {
        "summary": session.summary_snapshot,
        "text": summary_service.text_export(session.summary_snapshot),
        "generated_at": (
            session.summary_generated_at.isoformat() if session.summary_generated_at else None
        ),
    }


@router.post("/sessions/{session_id}/summary/regenerate")
def regenerate_summary(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    ensure_lifecycle(context, session, "close")
    snapshot = summary_service.store_snapshot(
        db, session=session, actor=context.actor, actor_name=context.name, regenerate=True
    )
    return {"summary": snapshot, "text": summary_service.text_export(snapshot)}


@router.get("/sessions/{session_id}/export.txt", response_class=PlainTextResponse)
def export_summary(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> str:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    snapshot = session.summary_snapshot or summary_service.build_snapshot(db, session)
    return summary_service.text_export(snapshot)


@router.get("/sessions/{session_id}/minutes.html", response_class=HTMLResponse)
def download_minutes(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> HTMLResponse:
    """The minutes, rendered from the frozen summary. Nothing is regenerated here."""
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    if session.summary_snapshot is None:
        raise AppError(
            "Close the meeting first and Mshikaki will write the minutes.",
            code="minutes.not_closed",
        )
    html = minutes_domain.render_minutes_html(
        session.summary_snapshot,
        team_name=context.team.name,
        reference=f"MSHIKAKI-{session.sequence_no}-{str(session.id)[:8]}",
    )
    filename = f"minutes-{session.sequence_no}.html"
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sessions/{session_id}/activity")
def session_activity(
    session_id: uuid.UUID,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    session = meetings.get_session(db, team_id=context.team.id, session_id=session_id)
    rows = activity_service.for_session(db, session_id=session.id)
    visible = can(context.actor, "activity.view.admin")
    return {
        "items": [activity_service.serialize(row, viewer_can_see_admin=visible) for row in rows]
    }
