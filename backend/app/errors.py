"""Error contract shared by every endpoint.

Every error answers with the same shape so the frontend can map failure to
friendly copy without guessing:

    {"error": {"code": "session.already_active", "message": "...", "details": {}}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for expected, user-facing failures."""

    code = "app.error"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Something went wrong."

    def __init__(
        self, message: str | None = None, *, code: str | None = None, **details: Any
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        # A per-instance code wins over the class default, so `AppError(..., code=...)`
        # behaves the way every caller expects.
        if code is not None:
            self.code = code
        self.details = details


class NotFoundError(AppError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class PermissionDeniedError(AppError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to do that."


class ConflictError(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "That conflicts with the current state."


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body(
                "request.invalid",
                "The request did not pass validation.",
                {"fields": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(f"http.{exc.status_code}", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Logged by the ASGI server; the client gets a stable, non-leaky message.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body("internal_error", "Something went wrong on our side."),
        )
