"""Public endpoints for the QR join flow."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session as DbSession

from app.api.auth import set_session_cookie
from app.config import Settings, get_settings
from app.deps import DbDep
from app.schemas import JoinRequest
from app.services import joining, meetings

router = APIRouter(tags=["join"])


@router.get("/join/{code}")
def preview(code: str, db: DbSession = DbDep) -> dict:  # type: ignore[assignment]
    """Safe for anyone with the link: it only names the team and the meeting."""
    return joining.preview(db, code)


@router.post("/join")
def join(
    payload: JoinRequest,
    response: Response,
    request: Request,
    db: DbSession = DbDep,  # type: ignore[assignment]
    settings: Settings = get_settings(),
) -> dict:
    user, membership, team, session, token = joining.join(
        db,
        code=payload.code,
        display_name=payload.display_name,
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    set_session_cookie(response, token=token, settings=settings)
    return {
        "user": {"id": str(user.id), "display_name": user.display_name, "email": user.email},
        "team": {"id": str(team.id), "name": team.name},
        "role": membership.role,
        # Sent so the browser can take them straight to the meeting they joined.
        "session": meetings.session_detail(db, session) if session is not None else None,
    }
