# Task: <short title>

## Source
- GitHub Issue: <link>

## Context
<what problem are we solving and why>

## Acceptance Criteria (must be testable)
- [ ] ...

## Test selection guide
Pick the cheapest test that proves the change:

1) **Backend unit/service tests (pytest)**: business logic, helpers.
2) **Backend API contract tests (pytest + FastAPI TestClient)**: endpoints, validation, responses.
3) **Frontend component tests (Vitest/Jest + React Testing Library)**: UI behavior (if web frontend exists).
4) **E2E smoke (Playwright)**: only for critical cross-stack flows.

## How to test locally
- Backend: `python -m pytest`

## Notes / Constraints
- Keep PR small and focused.
- If acceptance criteria can’t be tested, mark task as blocked and explain why.
