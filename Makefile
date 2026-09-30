# Mshikaki - common commands. Run `make help` for the list.
# Everything here is also documented in docs/development.md and docs/deployment.md.

SHELL := /bin/bash
BACKEND := backend
FRONTEND := frontend
COMPOSE := docker compose
DEV_COMPOSE := docker compose -f docker-compose.dev.yml
UV := uv run --all-extras

.DEFAULT_GOAL := help
.PHONY: help dev-db dev-db-stop api web migrate migration seed test test-backend test-frontend check lint fmt types build up down restart logs ps health backup restore shell db-shell clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev-db: ## Start local Postgres for development
	$(DEV_COMPOSE) up -d
	@echo "Postgres is up on localhost:5432"

dev-db-stop: ## Stop local Postgres
	$(DEV_COMPOSE) down

api: ## Run the API with reload on :8000
	cd $(BACKEND) && $(UV) uvicorn app.main:app --reload --port 8000

web: ## Run the frontend dev server on :5173
	cd $(FRONTEND) && npm run dev

migrate: ## Apply database migrations
	cd $(BACKEND) && $(UV) alembic upgrade head

migration: ## Create a migration: make migration name="add session lifecycle"
	@test -n "$(name)" || (echo 'Usage: make migration name="..."' && exit 1)
	cd $(BACKEND) && $(UV) alembic revision --autogenerate -m "$(name)"

seed: ## Load game definitions and content packs (idempotent)
	cd $(BACKEND) && $(UV) python -m app.cli seed

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd $(BACKEND) && $(UV) pytest

test-frontend: ## Run frontend tests
	cd $(FRONTEND) && npm test

lint: ## Lint the backend
	cd $(BACKEND) && $(UV) ruff check .

fmt: ## Format the backend
	cd $(BACKEND) && $(UV) ruff format .

types: ## Regenerate frontend types from the API schema
	./scripts/gen-types.sh

check: lint test ## Everything CI runs
	cd $(BACKEND) && $(UV) ruff format --check .
	cd $(FRONTEND) && npm run typecheck

build: ## Build the production image
	$(COMPOSE) build

up: ## Start the production stack (app + db)
	$(COMPOSE) up -d --build
	$(COMPOSE) ps

down: ## Stop the production stack
	$(COMPOSE) down

restart: ## Restart the app container
	$(COMPOSE) restart app

logs: ## Tail app logs
	$(COMPOSE) logs -f app

ps: ## Show container status
	$(COMPOSE) ps

health: ## Check the running app
	@curl -fsS http://localhost:$${APP_PORT:-8080}/api/health/ready && echo

backup: ## Dump the database to backups/
	./scripts/backup.sh

restore: ## Restore a dump: make restore file=backups/mshikaki-....sql.gz
	@test -n "$(file)" || (echo 'Usage: make restore file=backups/....sql.gz' && exit 1)
	./scripts/restore.sh $(file)

shell: ## Shell into the app container
	$(COMPOSE) exec app bash

db-shell: ## Open psql in the db container
	$(COMPOSE) exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

clean: ## Remove build artefacts and caches
	rm -rf $(FRONTEND)/dist
	find $(BACKEND) -type d -name __pycache__ -prune -exec rm -rf {} +
