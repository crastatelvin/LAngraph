# Contributing Guide

## Branching

- Create feature branches from `main`.
- Use clear names: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`.

## Required Before PR

- Map changes to task IDs in `TASKS.md`.
- Keep ADR decisions intact.
- Add tests for any behavior changes.
- Add audit/tenant checks for all API endpoints.

## Pull Request Checklist

- [ ] Linked to `TASKS.md` items
- [ ] Tests pass locally
- [ ] No secrets committed
- [ ] Docs updated where needed
- [ ] Feature flags used for advanced modules

## Code Standards

- Prefer typed interfaces and strict schemas.
- Keep logs structured and avoid sensitive data.
- Use small, reviewable PRs.
