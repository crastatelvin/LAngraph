# AI Parliament Cloud

AI Parliament Cloud is an industry-grade, multi-tenant SaaS for structured group decision-making using AI representatives, LangGraph orchestration, and explainable consensus.

## Current Status

This repository is initialized with a production-oriented foundation:
- monorepo layout for apps/packages/infra/tests
- FastAPI service starter with health endpoint
- shared schema package for debate contracts
- contribution and governance docs for public collaboration
- CI workflow for lint/test checks

## Monorepo Layout

```text
apps/
  api/      # FastAPI API service
  web/      # Frontend app placeholder
  worker/   # Background worker placeholder
packages/
  schemas/      # Shared Pydantic contracts
  graph-engine/ # LangGraph workflow package placeholder
infra/
  docker/   # Containerization assets
tests/
  integration/
docs/
  adr/
```

## Quickstart (API)

1. Create a virtual environment and install dependencies:
   - `pip install -r apps/api/requirements.txt`
2. Start API:
   - `uvicorn apps.api.main:app --reload --port 8000`
3. Verify:
   - `GET http://localhost:8000/health`

## Quickstart (Slack Worker)

Run outbound Slack queue worker:
- `python -m apps.worker.slack_outbound_worker`

## Database Migrations

- Create/update DB schema with Alembic:
  - `alembic upgrade head`
- Create new migration:
  - `alembic revision -m "your_message"`

## Collaboration

Please read:
- `PRD.md`
- `TASKS.md`
- `AI_PARLIAMENT_COMPLETE_HANDOFF.md`
- `docs/adr/*`
- `CONTRIBUTING.md`

## Roadmap

Execution follows `TASKS.md` phases with feature flags for advanced modules:
- `feature.agent_evolution`
- `feature.federation`
- `feature.governance_chain`
- `feature.slack`
