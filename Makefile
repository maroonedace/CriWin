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

# ---- Quality (mirrors CI) ----

.PHONY: test
test: ## Run the pytest suite
	$(PYTHON) -m pytest

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
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'
