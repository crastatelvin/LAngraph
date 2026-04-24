# TASKS - AI Parliament Cloud Build Board

## Usage Rules

- Execute phases in order.
- Every task must include tests and docs updates.
- No endpoint merges without auth, tenant checks, and audit logs.
- Keep advanced modules behind feature flags:
  - `feature.agent_evolution`
  - `feature.federation`
  - `feature.governance_chain`
  - `feature.slack`

## Phase 0 - Foundations

- [ ] T0.1 Create monorepo layout (`apps`, `packages`, `infra`, `docs`, `tests`).
- [ ] T0.2 Add shared schemas package and JSON schema CI checks.
- [ ] T0.3 Add auth/RBAC middleware and tenant resolver.
- [ ] T0.4 Add base observability (OTel traces, logs, metrics).
- [ ] T0.5 Configure CI: lint, typecheck, unit tests, vuln scan.
- [ ] T0.6 Add environment management and secrets policy.

## Phase 1 - Core MVP

### Backend
- [ ] T1.1 Implement `POST /v1/debates`.
- [ ] T1.2 Implement `GET /v1/debates/{id}` and `/events`.
- [ ] T1.3 Build LangGraph core nodes (normalize, opinion, debate, moderation, voting, consensus, persist).
- [ ] T1.4 Add strict structured-output parser with retries/fallback.
- [ ] T1.5 Add human approval endpoint (`/approve`) and policy gate.
- [ ] T1.6 Persist reports + audit events + cost stats.

### Frontend
- [ ] T1.7 Build dashboard with active debates and key metrics.
- [ ] T1.8 Build debate room with live rounds + agent panel.
- [ ] T1.9 Build decision report page with explainability tree.
- [ ] T1.10 Build replay UI for completed debates.

### Quality
- [ ] T1.11 Unit tests for consensus and parser fallback.
- [ ] T1.12 Integration tests for debate lifecycle.
- [ ] T1.13 E2E for create -> run -> approve flow.

## Phase 2 - Trust, Reliability, Security

- [ ] T2.1 Add fact-check and evidence scoring nodes.
- [ ] T2.2 Add calibration for confidence scoring.
- [ ] T2.3 Add policy engine for unsafe/insufficient evidence outcomes.
- [ ] T2.4 Add rate limits, request validation hardening, and WAF rules.
- [ ] T2.5 Add SLO dashboards and alerting.
- [ ] T2.6 Add runbooks for queue, model outage, Redis degradation.

## Phase 3 - Slack Integration

- [ ] T3.1 Implement Slack app setup and signed request verification.
- [ ] T3.2 Implement `/debate create` slash command.
- [ ] T3.3 Implement thread streaming updates per round.
- [ ] T3.4 Implement Approve/Reject action handlers.
- [ ] T3.5 Add idempotency and retry-safe event processing.
- [ ] T3.6 E2E integration test using sandbox workspace.

## Phase 4 - Federation

- [ ] T4.1 Implement federation entities and endpoints.
- [ ] T4.2 Implement signed summary exchange format.
- [ ] T4.3 Build federation consensus and dissent report.
- [ ] T4.4 Add federation map UI and session detail page.
- [ ] T4.5 Add load tests for multi-session federation.

## Phase 5 - Governance/Chain

- [ ] T5.1 Add chain adapter interface and provider config.
- [ ] T5.2 Implement `anchorDecision` and tx status retrieval.
- [ ] T5.3 Persist report hash and verification state.
- [ ] T5.4 Build governance panel with tx history.
- [ ] T5.5 Add deferred anchoring queue and retry logic.

## Phase 6 - Autonomous Agent Evolution

- [ ] T6.1 Add outcome ingestion pipeline.
- [ ] T6.2 Implement bounded trait update algorithm.
- [ ] T6.3 Implement profile versioning and rollback.
- [ ] T6.4 Add drift detector and alert rules.
- [ ] T6.5 Build evolution charts (calibration, reliability, trait deltas).
- [ ] T6.6 Add evaluation harness for improvement over baseline.

## Phase 7 - Billing and Admin

- [ ] T7.1 Implement usage metering events.
- [ ] T7.2 Implement plan limits and enforcement middleware.
- [ ] T7.3 Build admin pages for usage, policy, and API keys.
- [ ] T7.4 Exportable audit report endpoint.

## Phase 8 - Production Readiness

- [ ] T8.1 Add canary deployment + rollback automation.
- [ ] T8.2 Conduct security test pass (auth bypass, injection, tenant breakout).
- [ ] T8.3 Conduct load test pass and tune autoscaling.
- [ ] T8.4 Run game day drills and document incident postmortems.
- [ ] T8.5 Final release checklist and GA sign-off.

## Parallelization Lanes for IDE Agents

- Lane A: API + Graph + Data
- Lane B: Frontend UX + Realtime client
- Lane C: Integrations (Slack + Chain)
- Lane D: Reliability/SRE + Security
- Lane E: Test automation + load/security suites

## Done Criteria Per Task

- Code + tests + docs updated
- Lints/types pass
- No new high-severity security findings
- Metrics and logs emitted for new behavior

