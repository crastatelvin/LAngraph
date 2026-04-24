# ADR-002: Mandatory Human Approval for Final Decisions (Default)

## Status
Accepted

## Context
AI-generated consensus can be wrong, biased, or insufficiently evidenced. Enterprise trust and compliance require human accountability.

## Decision
All decision outputs are advisory by default and require explicit human approval before finalization, unless tenant policy opts into autonomous mode for low-risk classes.

## Consequences

### Positive
- Higher trust and accountability
- Better safety posture
- Clear legal/compliance boundary

### Negative
- Slightly slower decision closure
- Additional UX and workflow complexity

## Follow-ups
- Implement risk classification policy to optionally bypass gate for low-risk decisions.
- Record approver identity and timestamp in audit logs.

