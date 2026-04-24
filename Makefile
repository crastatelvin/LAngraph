.PHONY: help up down logs test migrate api worker

help:
	@echo "Available targets:"
	@echo "  make up       - Build and start API + worker via Docker Compose"
	@echo "  make down     - Stop Docker Compose services"
	@echo "  make logs     - Follow Docker Compose logs"
	@echo "  make test     - Run integration test suite"
	@echo "  make migrate  - Apply Alembic migrations"
	@echo "  make api      - Run API locally with uvicorn"
	@echo "  make worker   - Run Slack outbound worker locally"

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	pytest tests/integration -q

migrate:
	alembic upgrade head

api:
	uvicorn apps.api.main:app --reload --port 8000

worker:
	python -m apps.worker.slack_outbound_worker
