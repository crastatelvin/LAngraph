# PRD - AI Parliament Cloud

## 1. Product Summary

AI Parliament Cloud is a multi-tenant SaaS platform for structured group decision-making using AI representatives, debate workflows, and explainable consensus.

## 2. Problem

Teams and communities struggle to make high-quality decisions at scale because:
- chats are noisy and unstructured,
- polls lack reasoning,
- outcomes are hard to audit.

## 3. Goals

- Produce clear decision reports with evidence and minority views.
- Enable real-time collaboration across many participants.
- Maintain trust through human approval, explainability, and auditability.
- Support enterprise-grade SaaS operation (security, billing, SLOs).

## 4. Non-Goals (v1)

- Full autonomous policy governance with no human gate.
- Fully on-chain execution for all decisions.
- General-purpose social network features.

## 5. Users

- Org Admin: sets policies, manages integrations, sees audit/billing.
- Team Lead: starts debates, reviews outcomes, approves decisions.
- Member: contributes preferences and constraints.
- Auditor/Compliance: verifies history and traceability.

## 6. Core Use Cases

1. Team prioritization debate with 10-200 participants.
2. Slack-driven decision flow using slash command + thread updates.
3. Federation decision across multiple teams.
4. Governance mode that anchors final decision hash on chain.

## 7. Functional Requirements

### FR-1 Debate Lifecycle
- Create debate from proposal + constraints.
- Run structured multi-round agent debate.
- Output decision, confidence, risks, minority stance.
- Require human approval gate before final status.

### FR-2 Explainability
- Show argument timeline and evidence graph.
- Provide model and policy metadata in report.
- Replay any completed debate.

### FR-3 Agent Management
- Persistent per-user AI representative profile.
- Adjustable traits within policy bounds.
- Versioned profile updates and rollback.

### FR-4 Agent Evolution
- Ingest outcome quality signals.
- Recalibrate confidence and update traits with bounded deltas.
- Detect drift and alert.

### FR-5 Federation
- Create federation sessions from multiple parliaments.
- Exchange signed summaries.
- Produce global decision + dissent log.

### FR-6 Governance/Chain
- Anchor decision hash and retrieve tx status.
- Do not block decision flow on temporary chain failures.

### FR-7 Slack Integration
- Slash command to create debate.
- Threaded live updates.
- Approval actions from Slack.

### FR-8 SaaS Operations
- Multi-tenancy and RBAC.
- Usage metering and plan controls.
- Admin pages for policy/audit/usage.

## 8. Non-Functional Requirements

- 99.9% monthly uptime for API.
- Debate completion < 60s default scenario (3 rounds, <= 20 agents).
- Full audit trail for decision-critical actions.
- Tenant isolation enforced in app and DB access paths.
- Cost budget controls per tenant.

## 9. Success Metrics

- Debate completion success rate >= 95%.
- Human approval rate >= 70% after pilot tuning.
- Median decision turnaround reduced by >= 40% vs baseline process.
- p95 API latency for non-LLM endpoints < 700ms.
- Less than 2% schema-parse failure after retries.

## 10. Risks and Mitigations

- Hallucination risk -> evidence scoring + fact-check nodes + "inconclusive" mode.
- Bias amplification -> diversity regularization + dissent preservation.
- Scope creep -> phase-gated delivery + feature flags.
- Cost spikes -> model routing and budget caps.

## 11. Release Plan

- Alpha: internal tenant only, core debate + approval.
- Beta: add Slack + admin + usage.
- GA: federation + chain anchor + evolution.

## 12. MVP Exit Criteria

- End-to-end debate flow in web and Slack.
- Explainable report and replay.
- Audit and usage dashboards functional.
- On-call runbooks and canary rollback tested.

