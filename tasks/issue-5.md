# Task: Change submit button color to red

## Source
- GitHub Issue: https://github.com/adityasudhakar/number-adder/issues/5

## Context
Update the primary submit button in the web UI to be red (use existing styling system if present).\n\nAcceptance criteria:\n- The submit button appears red in the web UI.\n- No other buttons are unintentionally changed.\n\nNotes:\n- Prefer a class/token change over inline styles.\n- Add/adjust tests: component test preferred; E2E only if needed.

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
