# Task: Add support for adding 3 numbers (API + web UI)

## Source
- GitHub Issue: https://github.com/adityasudhakar/number-adder/issues/20

## Context
## Goal\nNumber-adder currently adds 2 numbers. Extend it to support adding 3 numbers, and keep the web UI consistent.\n\n## Scope\n- Backend API: support 3-number add\n- Web UI: always show 3 input fields for addition\n\n## Acceptance Criteria\n- API  accepts either 2 numbers (existing behavior) or 3 numbers and returns the correct sum.\n- Backward compatible: existing 2-number clients still work unchanged.\n- Web UI always shows three input fields for addition and submits all three.\n- Add/update pytest tests to cover both 2-number and 3-number cases.\n\n## Notes\n- Prefer minimal changes; avoid breaking multiply or auth flows.\n- If you need to choose a request format, prefer extending existing schema (e.g. optional ) over inventing a new endpoint.\n

## Acceptance Criteria (must be testable)
- [ ] (fill in)

## Test selection guide
Pick the cheapest test that proves the change:

1) **Backend unit/service tests (pytest)**: business logic, helpers.
2) **Backend API contract tests (pytest + FastAPI TestClient)**: endpoints, validation, responses.
3) **Frontend component tests (Vitest/Jest + React Testing Library)**: UI behavior (if web frontend exists).
4) **E2E smoke (Playwright)**: only for critical cross-stack flows.

## How to test locally
- Backend: `python -m pytest`
- Frontend (if applicable): `npm test`

## Notes / Constraints
- Keep PR small and focused.
- If acceptance criteria can’t be tested, mark task as blocked and explain why.
