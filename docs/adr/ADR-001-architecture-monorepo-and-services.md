# ADR-001: Monorepo with Modular Service Boundaries

## Status
Accepted

## Context
The platform has multiple fast-evolving domains (graph engine, integrations, UI, governance). A single codebase is desired for velocity, but clear module boundaries are needed to avoid coupling.

## Decision
Use a monorepo with:
- deployable apps (`web`, `api`, `worker`)
- domain packages (`graph-engine`, `consensus-core`, `memory-core`, integrations)
- shared schemas package as source of truth.

## Consequences

### Positive
- Faster cross-team iteration
- Shared type/schema consistency
- Easier CI governance

### Negative
- Requires stricter ownership and code review rules
- Build graph can become complex without tooling discipline

## Follow-ups
- Enforce ownership map and CODEOWNERS.
- Add schema compatibility checks in CI.

