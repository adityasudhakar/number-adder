# Task: Add a /subtract endpoint that subtracts two numbers

## Source
- GitHub Issue: https://github.com/adityasudhakar/number-adder/issues/23

## Context
Add a new API endpoint `/subtract` that accepts two numbers and returns their difference.

**Requirements:**
- Endpoint: `POST /subtract` or `GET /subtract?a=X&b=Y`
- Returns: `{"result": a - b}`
- Add tests confirming `5 - 3 = 2`, `0 - 5 = -5`, `10 - 10 = 0`
- Update web UI to include subtract functionality

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
