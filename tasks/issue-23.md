# Task: Add a /subtract endpoint that subtracts two numbers

## Context
Implement a new API endpoint `/subtract` that accepts two numbers and returns their difference.

## Scope
- Create the endpoint `POST /subtract` and/or `GET /subtract?a=X&b=Y`.
- Ensure the response format is `{"result": a - b}`.
- Implement unit tests for the following cases:
  - `5 - 3 = 2`
  - `0 - 5 = -5`
  - `10 - 10 = 0`
- Update the web UI to include functionality for subtraction.

## Non-goals
- Do not modify existing endpoints unrelated to subtraction.
- Do not implement additional mathematical operations.

## Acceptance Criteria
- [ ] The endpoint `POST /subtract` returns `{"result": 2}` for input `{"a": 5, "b": 3}`.
- [ ] The endpoint `GET /subtract?a=0&b=5` returns `{"result": -5}`.
- [ ] The endpoint `GET /subtract?a=10&b=10` returns `{"result": 0}`.
- [ ] Unit tests for the above cases are implemented and pass successfully.
- [ ] The web UI includes a functional component for subtraction.

## Implementation Notes
- Follow existing code style and conventions.
- Ensure proper error handling for invalid inputs (e.g., non-numeric values).

## Test Plan
1. **Backend Unit Tests**: Use `pytest` to validate business logic for subtraction.
2. **API Contract Tests**: Use `pytest` with FastAPI TestClient to verify endpoint responses.
3. **Frontend Component Tests**: If applicable, use Vitest/Jest with React Testing Library to test UI behavior.

## Rollback/Safety
- If issues arise during deployment, revert to the previous stable commit.
- Ensure all tests pass before merging to the main branch.

---

_Spec upgraded by manager: 2023-10-01T12:00:00Z_