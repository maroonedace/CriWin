.PHONY: dev dev-down prod prod-down logs

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
