# ADR-003: Postgres + Redis + Vector Memory with Tenant Isolation

## Status
Accepted

## Context
The system needs reliable transactional records, realtime transport, and semantic retrieval for agent memory, all under strict tenant isolation.

## Decision
- Use Postgres for relational truth (tenants, debates, votes, decisions, audit, billing).
- Use Redis for queueing, pub/sub, cache, and idempotency keys.
- Use vector memory (pgvector or managed vector DB) for semantic memory retrieval.
- Enforce tenant isolation keys in all stores and access APIs.

## Consequences

### Positive
- Strong operational baseline
- Supports replay, audit, and analytics
- Flexible memory retrieval options

### Negative
- More moving parts than single-store setup
- Requires rigorous data lifecycle policies

## Follow-ups
- Add tenant-isolation test suite.
- Add retention/deletion workflows and compliance docs.

