# Mshikaki production image.
#
# One image, two stages:
#   web  -> builds the React SPA into /web/dist
#   api  -> installs the FastAPI backend and serves the built SPA as static files
#
# The result is a single container answering both /api/* and the browser app,
# which keeps deployment at two containers (app + Postgres) and removes CORS,
# a reverse proxy and a second published port from the picture.
#
# Build from the repository root:  docker compose build

# ---------------------------------------------------------------- web build ---
FROM node:22-alpine AS web

WORKDIR /web

# Dependencies first so this layer survives source changes.
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/ ./
RUN npm run build

# -------------------------------------------------------------- api runtime ---
FROM python:3.12-slim AS api

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl is used by the container health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ ./
RUN python -m pip install --upgrade pip && python -m pip install .

# Game content is a product asset, not backend code, but the image needs it: the
# seeder reads these files at start-up.
COPY content/ ./content/
ENV CONTENT_DIR=/app/content/packs

COPY --from=web /web/dist ./static

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
