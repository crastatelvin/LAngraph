# ADR-004: Structured LLM Outputs with Retry/Fallback Policy

## Status
Accepted

## Context
Unstructured model outputs create brittle parsing and hidden failures in multi-step workflows.

## Decision
- Every graph node must return schema-validated JSON.
- Parse failures trigger bounded retries.
- If still failing, route to fallback model/template.
- If still failing, emit safe failure state (`inconclusive` or `needs_more_input`).

## Consequences

### Positive
- Deterministic orchestration
- Better reliability and debuggability
- Lower incident rates from malformed outputs

### Negative
- Slightly higher token/latency overhead due to retries
- More strict prompt engineering and validation code

## Follow-ups
- Track parse failure rate metric per node and model.
- Add contract tests for all node schemas.

