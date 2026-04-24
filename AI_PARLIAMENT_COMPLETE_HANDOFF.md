# AI Parliament - Complete Industry-Grade Build Handoff

## 1) Mission and Product Scope

Build a multi-tenant SaaS platform where groups make high-quality decisions through:
- persistent AI representatives per user,
- structured multi-agent debate workflows,
- explainable consensus reports,
- real-time collaboration,
- optional federation and blockchain verification.

Primary v1 users:
- Product and engineering teams
- Community/operations teams
- Governance-heavy organizations

---

## 2) Feature Set (All Included)

### Core Decision Engine
- Proposal intake with constraints and success criteria
- Multi-agent opinion generation
- Multi-round debate with moderator
- Structured voting with confidence
- Consensus report with risks + minority views
- Replayable decision timeline

### Autonomous Agent Evolution
- Track outcome quality per decision
- Update agent trait weights with bounded learning
- Calibration scoring (confidence vs correctness)
- Drift detection and rollback to prior profile version

### Multi-Parliament Federation
- Independent parliaments per org/team
- Cross-parliament summary exchange
- Federation-level consensus and conflict resolution
- Treaty mode for negotiated final outputs

### DAO + Blockchain Voting
- Optional on-chain anchor for final decision hash
- Optional vote notarization per parliament session
- Wallet-bound identity mapping for governance mode

### Real-Time Slack Integration
- Slash command to create debate
- Threaded updates per round
- Interactive approval/reject actions
- Final report postback with deep links

### SaaS Essentials
- Multi-tenancy + RBAC
- Billing and usage metering
- Admin console
- Audit logs and policy controls
- Observability + alerting

---

## 3) Hard Non-Functional Requirements

- API p95 < 700ms for non-LLM endpoints
- Debate completion target < 60s for default 3-round flow
- 99.9% monthly API availability
- Full traceability of decisions (inputs, prompts, model versions, outputs)
- Tenant data isolation by design and tests
- Cost control via model routing + budget enforcement

---

## 4) Recommended Stack

### Frontend
- Next.js (App Router), TypeScript, Tailwind, shadcn/ui
- Zustand or React Query for client state
- WebSocket + SSE fallback
- Recharts + React Flow for explainability graphs

### Backend
- FastAPI + Pydantic v2
- LangChain + LangGraph
- Celery (or Temporal) for long-running orchestration
- Redis for queue, pub/sub, locks

### Data
- Postgres (primary relational + audit + billing)
- pgvector (or Pinecone) for memory retrieval
- Object storage (S3/GCS) for artifacts/reports

### Infra/DevOps
- Docker + Kubernetes (EKS/GKE/AKS) or ECS/Cloud Run initially
- GitHub Actions CI/CD
- OpenTelemetry + Prometheus + Grafana + Loki
- Secret manager (AWS Secrets Manager/GCP Secret Manager)

---

## 5) Repository Structure

```text
ai-parliament/
  apps/
    web/                          # Next.js frontend
    api/                          # FastAPI public API
    worker/                       # queue workers / long jobs
  packages/
    graph-engine/                 # LangGraph nodes + workflow
    agent-core/                   # agent profile/evolution logic
    consensus-core/               # scoring, calibration, fairness
    memory-core/                  # retrieval, memory versioning
    integrations-slack/           # Slack adapters
    integrations-chain/           # blockchain adapters
    sdk/                          # TS/Python client SDKs
    schemas/                      # shared JSON schemas
  infra/
    terraform/
    k8s/
    docker/
  docs/
    architecture/
    runbooks/
    adrs/
  tests/
    e2e/
    load/
    security/
```

---

## 6) Domain Model (Minimum)

### Core tables
- `tenants(id, name, plan, created_at)`
- `users(id, tenant_id, email, role, auth_provider_id, created_at)`
- `agents(id, tenant_id, user_id, profile_json, version, calibration_score, created_at)`
- `debates(id, tenant_id, proposal, status, rounds, created_by, created_at, completed_at)`
- `debate_events(id, debate_id, seq, type, payload_json, created_at)`
- `votes(id, debate_id, agent_id, vote, confidence, evidence_score, created_at)`
- `decisions(id, debate_id, result, confidence, report_json, report_hash, created_at)`
- `agent_outcomes(id, agent_id, debate_id, outcome_score, created_at)`
- `federations(id, tenant_id, name, created_at)`
- `federation_sessions(id, federation_id, status, created_at)`
- `billing_usage(id, tenant_id, metric, quantity, period_start, period_end)`
- `audit_logs(id, tenant_id, actor_id, action, resource, payload_json, created_at)`

---

## 7) API Contract (Core)

### Debate
- `POST /v1/debates`
- `GET /v1/debates/{id}`
- `GET /v1/debates/{id}/events`
- `POST /v1/debates/{id}/approve` (human gate)

### Agents
- `GET /v1/agents`
- `PATCH /v1/agents/{id}` (traits/policy bounds)
- `POST /v1/agents/{id}/recalibrate`

### Federation
- `POST /v1/federations`
- `POST /v1/federations/{id}/sessions`
- `POST /v1/federations/sessions/{id}/join`
- `GET /v1/federations/sessions/{id}/decision`

### Blockchain
- `POST /v1/chain/anchor-decision`
- `GET /v1/chain/tx/{hash}`

### Slack
- `POST /v1/integrations/slack/events`
- `POST /v1/integrations/slack/commands`

### Admin/Billing
- `GET /v1/admin/usage`
- `GET /v1/admin/audit`
- `GET /v1/admin/slo`

---

## 8) LangGraph Workflow (Production)

Nodes:
1. `normalize_proposal`
2. `fetch_agent_context`
3. `generate_initial_opinions`
4. `debate_round`
5. `moderate_round`
6. `fact_check`
7. `score_evidence`
8. `vote_structured`
9. `consensus_compute`
10. `human_gate`
11. `persist_artifacts`
12. `emit_realtime_events`

Loop rule:
- Repeat `debate_round -> moderate_round -> fact_check -> score_evidence` until:
  - `round >= max_rounds`, or
  - convergence threshold reached, or
  - budget exhausted.

Failure paths:
- schema parse fail -> retry (max 2) -> fallback model -> safe abort
- low evidence quality -> `insufficient_evidence` outcome
- policy violation -> blocked with compliance reason

---

## 9) Consensus Algorithm (Industry Grade)

Compute per agent:
- stance score: YES=+1, NO=-1
- confidence (calibrated)
- evidence quality score (citation/fact-check weighted)
- expertise relevance score
- historical reliability score
- diversity regularization factor (prevent monoculture bias)

Weighted score:

`final = sum(stance * conf_calibrated * evidence * expertise * reliability * diversity_factor) / sum(weights)`

Outputs:
- decision (`APPROVED`/`REJECTED`/`INCONCLUSIVE`)
- confidence band (`low/medium/high`)
- top supporting arguments
- top risks
- minority position block

Guardrails:
- minimum evidence threshold for high-confidence decisions
- confidence cannot exceed calibration ceiling
- forced inconclusive if disagreement + low evidence

---

## 10) Autonomous Agent Evolution

### Learning loop
After each decision outcome window closes:
1. ingest result quality score (manual + KPI-based)
2. compare predicted confidence vs actual outcome
3. update reliability and calibration
4. bounded trait updates (max delta per cycle)
5. write new profile version (`agents.version + 1`)

### Safety
- no self-modification outside trait allowlist
- mandatory changelog with reason codes
- one-click rollback to previous profile version
- anomaly detector for sudden behavior drift

---

## 11) Federation Design

Federation flow:
1. each parliament runs local debate
2. each submits signed summary artifact
3. federation mediator runs cross-summary reasoning
4. conflict resolution round if divergence above threshold
5. global decision with per-parliament dissent log

Controls:
- configurable parliament weights
- domain-based authority routing
- quorum requirements for federation decision

---

## 12) DAO / Blockchain Module

Use optional governance mode:
- anchor `decision_report_hash` on-chain
- optionally record aggregated vote proof
- maintain off-chain canonical report for rich explainability

Minimum contract functions:
- `anchorDecision(bytes32 reportHash, string debateId)`
- `getDecisionAnchor(string debateId)`

Best practice:
- use testnet first
- abstract chain provider behind adapter
- never block product flow on chain failure (deferred anchor queue)

---

## 13) Slack Integration

Features:
- `/debate create <proposal>`
- app posts debate card + live round updates in thread
- action buttons: Approve / Request More Evidence / Reject
- final decision summary with confidence and risk bullets

Technical:
- verify Slack signatures
- idempotency key by `event_id`
- retry-safe handlers
- map Slack workspace/channel to tenant/project

---

## 14) Frontend UI (Killer Control-Room UX)

Screens:
1. Dashboard: active debates, consensus trend, spend, latency
2. Debate Room: agent panel, live argument stream, round timeline
3. Decision Report: confidence, evidence tree, minority views
4. Agent Evolution: calibration and trait changes over time
5. Federation Map: parliament graph + session outcomes
6. Governance: on-chain anchors and tx status
7. Admin: policy, budgets, audit, API keys

UX must-haves:
- live updates with sequence integrity
- explainability graph (why decision happened)
- replay mode for past debates
- explicit human approval gate in UI

---

## 15) Security and Compliance

- OIDC auth (Auth0/Clerk) + RBAC + tenant scoping middleware
- encryption at rest and in transit
- secrets in managed vault, never in code
- WAF + API rate limiting + bot protection
- prompt injection filtering and tool-call allowlist
- audit all sensitive actions
- data retention + deletion workflows (GDPR-ready)

---

## 16) Observability and SRE

Emit:
- traces for each graph node
- tokens, latency, cost per debate
- parse failure rates, fallback rates
- consensus quality and override frequency

SLO alerts:
- debate timeout breach
- error spike
- cost anomaly
- websocket delivery failure

Runbooks required:
- queue backlog incident
- model provider outage
- Redis degradation
- chain anchor failure fallback

---

## 17) Testing Strategy

### Unit
- consensus math
- agent evolution bounds
- policy validators

### Integration
- full graph happy path
- schema/fallback paths
- tenant isolation

### E2E
- create debate -> rounds -> decision -> approval
- Slack command to completion
- chain anchor verification

### Non-functional
- load test 1k concurrent debate sessions
- chaos test model timeout and Redis failover
- security test for prompt injection + auth bypass

---

## 18) CI/CD

Pipeline stages:
1. lint + typecheck
2. unit/integration tests
3. contract/schema compatibility checks
4. image build + SBOM + vulnerability scan
5. deploy to staging
6. smoke + synthetic tests
7. manual gate for production
8. canary deploy + rollback automation

---

## 19) Delivery Plan (Do Not Skip)

### Phase 1 (Weeks 1-3) - Production MVP
- Core graph workflow
- Debate + decision report
- Human approval gate
- Realtime UI
- Audit + basic billing usage

### Phase 2 (Weeks 4-5) - Trust and Reliability
- Evidence scoring + calibration
- robust retries/fallbacks
- observability + SLO dashboards
- security hardening

### Phase 3 (Weeks 6-7) - Integrations
- Slack end-to-end
- federation v1
- chain anchor v1

### Phase 4 (Week 8+) - Autonomous Evolution
- outcome ingestion
- trait evolution with guardrails
- drift detection and rollback UI

---

## 20) Acceptance Criteria (Definition of Done)

Project is complete only when all are true:
- all endpoints implemented and documented
- deterministic JSON schema outputs for every node
- 95%+ successful debate completion in staging tests
- p95 latency and cost budgets met
- full audit trail for every decision
- Slack flow works in production workspace
- federation session produces global decision with dissent report
- chain anchor created and verifiable from report hash
- agent evolution updates versioned profiles with rollback
- CI/CD with canary + rollback proven in drill

---

## 21) Build Instructions for IDE Agents (Execution Prompt)

Use this exact instruction template when delegating:

1. Implement by phase order; do not skip prerequisites.
2. Generate code only from typed schemas and contracts in `/packages/schemas`.
3. For every new endpoint, add:
   - request/response schema,
   - auth + tenant checks,
   - unit + integration tests,
   - audit logging.
4. For every LangGraph node, enforce structured output parsing with retries/fallback.
5. Add OpenTelemetry spans and metrics per node.
6. Keep all feature flags configurable (`federation`, `governance_mode`, `agent_evolution`).
7. Do not remove human approval gate unless explicitly configured.
8. Update docs and runbooks with each merged feature.

---

## 22) Final Notes

- This handoff includes all requested features and a realistic delivery order.
- Build sequence matters more than feature count.
- If forced to launch early, ship Phase 1 + 2 first, then enable advanced modules behind feature flags.

