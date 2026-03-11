# Task: Add /multiply endpoint

## Source
- GitHub Issue: https://github.com/adityasudhakar/number-adder/issues/27

## Context
Add a new API endpoint that multiplies two numbers.

**Requirements:**
- Endpoint: `GET /multiply?a=X&b=Y` 
- Returns: `{"result": X * Y}`
- Add tests for: 3*4=12, 0*5=0, -2*3=-6

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
