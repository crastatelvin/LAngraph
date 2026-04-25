# Canary Rollback Drill Runbook

This runbook documents how to execute and verify a canary + rollback drill for AI Parliament Cloud.

## Objective

- Prove we can gate promotion using quality/security/load checks.
- Prove rollback path is fast and repeatable.
- Capture evidence for production readiness.

## Prerequisites

- CI green on current branch.
- Migration state up to date (`alembic upgrade head`).
- Staging environment available.
- On-call owner assigned for the drill window.

## Trigger Workflow

Use GitHub Actions workflow:
- `.github/workflows/canary-rollback-drill.yml`

Required manual inputs:
- `environment` (default `staging`)
- `canary_percent` (default `10`)
- `rollback_on_failure` (default `true`)

## Drill Procedure

1. Trigger workflow manually (`workflow_dispatch`).
2. Confirm safety gate executes:
   - integration tests
   - security harness
   - load smoke harness
3. If all gates pass:
   - workflow performs simulated canary promotion step
4. If any gate fails and rollback is enabled:
   - workflow performs simulated rollback step

## Verification Checklist

- [ ] Drill run has a GitHub Actions URL and timestamp.
- [ ] Safety gate logs are attached in the run.
- [ ] Canary promotion step outcome recorded.
- [ ] Rollback step tested at least once this sprint (intentional failure drill acceptable).
- [ ] Post-drill notes captured in incident template.

## Failure Injection (Recommended)

At least once per sprint, intentionally break one gate in a temporary branch:
- Example: set an unrealistically strict load threshold in `tests/nonfunctional/test_load_smoke.py`.
- Confirm rollback path executes.
- Revert threshold immediately after evidence capture.

## Evidence to Keep

- Workflow run URL
- Job summary
- Gate logs
- Rollback timestamp (if triggered)
- Follow-up actions
