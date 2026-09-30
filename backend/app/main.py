"""FastAPI application factory.

Responsibilities, in order:
  1. Build the app and register error handlers.
  2. Register the API routers under /api.
  3. Serve the built single-page app, in production only.

In development the SPA is served by Vite, which proxies /api to this process, so
the static mount below finds no directory and is skipped.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import health
from app.config import Settings, get_settings
from app.errors import register_error_handlers
from app.logging_setup import configure_logging

logger = logging.getLogger("mshikaki")

API_PREFIX = "/api"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Mshikaki API",
        version=__version__,
        description=(
            "Meetings that produce decisions, work and a record. "
            "See docs/14-implementation-plan.md in the repository."
        ),
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    register_error_handlers(app)

    if settings.is_development:
        # Only the Vite dev server needs this. Production is same-origin.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router, prefix=API_PREFIX)

    mount_spa(app, settings)
    return app


def mount_spa(app: FastAPI, settings: Settings) -> None:
    """Serve the built SPA from FastAPI when it exists.

    Mounted after the API routes, so /api/* always wins. Unknown /api paths return
    JSON 404 rather than the HTML shell, which keeps client bugs obvious.
    """
    static_dir: Path = settings.static_dir
    index_file = static_dir / "index.html"
    if not index_file.is_file():
        logger.info("No built frontend at %s; running API only.", static_dir)
        return

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        # Hashed asset filenames can be cached aggressively.
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Unknown API endpoint")

        candidate = (static_dir / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(static_dir.resolve()):
            return FileResponse(candidate)

        # Client-side routes (for example /sessions/123) fall back to the shell.
        return FileResponse(index_file)

    logger.info("Serving built frontend from %s", static_dir)


app = create_app()
