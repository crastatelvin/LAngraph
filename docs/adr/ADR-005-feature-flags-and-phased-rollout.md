# ADR-005: Feature Flags for Advanced Modules

## Status
Accepted

## Context
Advanced capabilities (federation, governance chain, autonomous evolution) increase risk and complexity. They should not block core product stability.

## Decision
Gate advanced modules behind feature flags and release in phases:
- Core debate + approval first
- Reliability and security second
- Integrations and advanced modules after baseline SLOs are met

## Consequences

### Positive
- Safer releases
- Easier experimentation by tenant/segment
- Better rollback and incident control

### Negative
- More configuration complexity
- Need strong flag hygiene and cleanup process

## Follow-ups
- Add centralized flag registry and ownership.
- Add kill-switch controls in admin console.

