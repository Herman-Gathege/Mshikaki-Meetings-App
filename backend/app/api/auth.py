"""Registration, sign in, sign out and the current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as DbSession

from app.config import Settings, get_settings
from app.db.models import User
from app.deps import SESSION_COOKIE, ContextDep, DbDep
from app.errors import AppError
from app.schemas import LoginRequest, PreferencesRequest, RegisterRequest
from app.services import auth as auth_service
from app.services import identity

router = APIRouter(tags=["auth"])


def set_session_cookie(response: Response, *, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.session_ttl_days * 24 * 3600,
        path="/",
    )


def _user_payload(user: User, context) -> dict:
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "timezone": user.timezone,
            "leaderboard_opt_out": user.leaderboard_opt_out,
        },
        "team": {
            "id": str(context.team.id),
            "name": context.team.name,
            "timezone": context.team.timezone,
        },
        "role": context.membership.role,
    }


@router.get("/auth/me")
def me(context=ContextDep) -> dict:
    return _user_payload(context.user, context)


@router.post("/auth/register")
def register(
    payload: RegisterRequest,
    response: Response,
    request: Request,
    db: DbSession = DbDep,  # type: ignore[assignment]
    settings: Settings = Depends(get_settings),
) -> dict:
    invite = None
    if payload.invite_code:
        invite = identity.find_invite(db, payload.invite_code)

    user, membership, team = auth_service.register(
        db,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        team_name=payload.team_name,
        invite=invite,
    )

    token = auth_service.start_auth_session(
        db, user=user, user_agent=request.headers.get("user-agent")
    )
    set_session_cookie(response, token=token, settings=settings)
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
        },
        "team": {"id": str(team.id), "name": team.name},
        "role": membership.role,
    }


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: DbSession = DbDep,  # type: ignore[assignment]
    settings: Settings = Depends(get_settings),
) -> dict:
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    membership = auth_service.active_membership(db, user.id)
    if membership is None:
        raise AppError("That account is not part of a team yet.", code="team.missing")

    token = auth_service.start_auth_session(
        db, user=user, user_agent=request.headers.get("user-agent")
    )
    set_session_cookie(response, token=token, settings=settings)
    return {
        "user": {"id": str(user.id), "email": user.email, "display_name": user.display_name},
        "team": {"id": str(membership.team_id), "name": ""},
        "role": membership.role,
    }


@router.post("/auth/logout")
def logout(
    response: Response,
    request: Request,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth_service.end_auth_session(db, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "signed_out"}


@router.patch("/me/preferences")
def update_preferences(
    payload: PreferencesRequest,
    context=ContextDep,
    db: DbSession = DbDep,  # type: ignore[assignment]
) -> dict:
    if payload.leaderboard_opt_out is not None:
        context.user.leaderboard_opt_out = payload.leaderboard_opt_out
    if payload.display_name is not None and payload.display_name.strip():
        context.user.display_name = payload.display_name.strip()
    return {
        "display_name": context.user.display_name,
        "leaderboard_opt_out": context.user.leaderboard_opt_out,
    }
