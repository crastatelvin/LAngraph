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
2. Copy env template:
   - `cp .env.example .env` (Linux/macOS)
   - `copy .env.example .env` (Windows CMD)
   - `Copy-Item .env.example .env` (PowerShell)
3. Update `.env` values as needed (especially Slack secrets if using integrations).
4. Start API:
   - `uvicorn apps.api.main:app --reload --port 8000`
5. Verify:
   - `GET http://localhost:8000/health`

## Quickstart (Slack Worker)

Run outbound Slack queue worker:
- `python -m apps.worker.slack_outbound_worker`

## Slack Integration Cookbook

### 1) Configure environment

Set the following in `.env`:
- `ENABLE_SLACK_INTEGRATION=true`
- `SLACK_SIGNING_SECRET=<from Slack app settings>`
- `SLACK_BOT_TOKEN=<xoxb token>`
- `FEDERATION_SLACK_CHANNEL=<optional channel id for federation queue updates>`

Then start API + worker:
- `uvicorn apps.api.main:app --reload --port 8000`
- `python -m apps.worker.slack_outbound_worker`

### 2) Slack request URLs

Point Slack app endpoints to your API:
- Events: `POST /v1/integrations/slack/events`
- Slash commands: `POST /v1/integrations/slack/commands`
- Interactions: `POST /v1/integrations/slack/interactions`

### 3) Debate flow commands

- `/debate <proposal text>`
  - Creates debate under tenant `slack-<team_id>`
  - Returns interactive buttons:
    - `Approve` -> approves debate
    - `Reject` -> rejects debate

### 4) Federation flow commands

- `/federation create-session <federation_id>`
  - Creates open federation session
  - Returns stance buttons:
    - `Approve`
    - `Reject`
    - `Inconclusive`

- `/federation decision <session_id>`
  - Returns latest consensus snapshot:
    - decision
    - confidence
    - submission count

- `/federation submissions <session_id>`
  - Returns compact submission history summary (position/confidence/weight).

### 5) Operational checks

- Queue status:
  - `GET /v1/integrations/slack/outbound/status`
- Force flush:
  - `POST /v1/integrations/slack/outbound/flush`
- Cleanup old Slack state:
  - `POST /v1/admin/slack/cleanup`

## Quickstart (Docker Compose)

Run API + worker together:
- `docker compose up --build`

API endpoint:
- `http://localhost:8000/health`

You can also pass env values to Compose via:
- `docker compose --env-file .env up --build`

## Developer Shortcuts (Makefile)

- `make up` -> start API + worker via Docker Compose
- `make down` -> stop services
- `make logs` -> stream service logs
- `make test` -> run integration tests
- `make load-smoke` -> run non-functional load smoke tests
- `make migrate` -> run Alembic migrations
- `make api` -> run API locally
- `make worker` -> run Slack outbound worker locally

## Load Smoke Harness

A lightweight non-functional baseline is included in:
- `tests/nonfunctional/test_load_smoke.py`

Current smoke coverage:
- Health endpoint p95 latency check
- Debate creation success-rate + average latency check

Run locally:
- `pytest tests/nonfunctional -q`
- or `make load-smoke`

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
- `docs/runbooks/canary_rollback_drill.md`
- `docs/runbooks/incident_postmortem_template.md`
- `CONTRIBUTING.md`

## Canary and Rollback Drill

A manual drill workflow is available:
- `.github/workflows/canary-rollback-drill.yml`

Use it to run:
- integration gates
- security harness
- load smoke harness
- simulated canary promotion and rollback branches

Operational guide:
- `docs/runbooks/canary_rollback_drill.md`

## Roadmap

Execution follows `TASKS.md` phases with feature flags for advanced modules:
- `feature.agent_evolution`
- `feature.federation`
- `feature.governance_chain`
- `feature.slack`
