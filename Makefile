# Criwin task runner. Run `make` or `make help` to list targets.
#
# Dev targets use docker-compose.yml + docker-compose.override.yml (auto-merged).
# Prod targets add docker-compose.prod.yml and read env from $(PROD_ENV), which
# skips the dev override so source mounts never reach production.

COMPOSE  := docker compose
PROD_ENV ?= .env.prod
PROD     := docker compose --env-file $(PROD_ENV) -f docker-compose.yml -f docker-compose.prod.yml
PYTHON   ?= python

.DEFAULT_GOAL := help

# ---- Development (macOS / Windows / Linux) ----

.PHONY: up
up: ## Build and start the dev stack (detached)
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Stop the dev stack
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart app + admin to pick up local source edits
	$(COMPOSE) restart app admin

.PHONY: logs
logs: ## Follow logs for all dev services
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show dev service status
	$(COMPOSE) ps

.PHONY: config
config: ## Print the merged dev compose config
	$(COMPOSE) config

# ---- Database migrations ----

.PHONY: migrate
migrate: ## Bring the dev database up to head
	$(COMPOSE) run --rm migrate

.PHONY: revision
revision: ## Autogenerate a migration from the models: make revision m="add widgets"
	@test -n "$(m)" || { echo 'usage: make revision m="describe the change"'; exit 1; }
	$(COMPOSE) run --rm --user $(shell id -u):$(shell id -g) migrate \
		alembic revision --autogenerate -m "$(m)"

.PHONY: migrate-down
migrate-down: ## Roll the dev database back one revision
	$(COMPOSE) run --rm migrate alembic downgrade -1

.PHONY: migrate-status
migrate-status: ## Show the dev database's current revision
	$(COMPOSE) run --rm migrate alembic current --verbose

# ---- Production (Debian server) ----

.PHONY: prod-up
prod-up: ## Build and start the prod stack (detached)
	$(PROD) up -d --build

.PHONY: prod-down
prod-down: ## Stop the prod stack
	$(PROD) down

.PHONY: prod-logs
prod-logs: ## Follow logs for all prod services
	$(PROD) logs -f

.PHONY: prod-ps
prod-ps: ## Show prod service status
	$(PROD) ps

.PHONY: prod-config
prod-config: ## Print the merged prod compose config
	$(PROD) config

.PHONY: prod-migrate
prod-migrate: ## Bring the prod database up to head (runs on its own, before prod-up)
	$(PROD) run --rm migrate

# ---- Quality (mirrors CI) ----

.PHONY: test
test: ## Run the pytest suite
	$(PYTHON) -m pytest

.PHONY: test-db
test-db: ## Start a throwaway Postgres for the database-backed tests
	docker run --rm -d --name criwin-test-db -p 5432:5432 \
		-e POSTGRES_USER=criwin -e POSTGRES_PASSWORD=criwin -e POSTGRES_DB=criwin_test \
		postgres:16-alpine

.PHONY: test-db-stop
test-db-stop: ## Stop the throwaway test Postgres
	docker rm -f criwin-test-db

.PHONY: lint
lint: ## Ruff lint + format check
	ruff check .
	ruff format --check .

.PHONY: fmt
fmt: ## Auto-format with Ruff
	ruff format .

# ---- Meta ----

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
