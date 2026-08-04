PYTHON ?= python3.12


.PHONY: dev dev-down prod prod-down logs install-dev test

install-dev:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

test:
	.venv/bin/pytest

dev:
	ENV_FILE=.env.development docker compose up --build -d

dev-down:
	ENV_FILE=.env.development docker compose down

prod:
	ENV_FILE=.env.production docker compose up --build -d

prod-down:
	ENV_FILE=.env.production docker compose down

logs:
	docker compose logs -f
