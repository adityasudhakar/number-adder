# Task: Add /multiply endpoint

## Context
We need to implement a new API endpoint that multiplies two numbers provided as query parameters.

## Scope
- Implement the endpoint `GET /multiply?a=X&b=Y`.
- Ensure the response format is `{"result": X * Y}`.
- Include unit tests to validate the multiplication logic.

## Non-goals
- This task does not include any frontend changes or UI components.

## Acceptance Criteria
- [ ] The endpoint `GET /multiply?a=X&b=Y` returns a JSON response with the correct multiplication result.
- [ ] The following test cases are implemented and pass:
  - Input: `3` and `4`, Output: `{"result": 12}`
  - Input: `0` and `5`, Output: `{"result": 0}`
  - Input: `-2` and `3`, Output: `{"result": -6}`

## Implementation Notes
- Use the existing API framework (e.g., FastAPI) to create the endpoint.
- Ensure proper validation of input parameters (X and Y should be numbers).

## Test Plan
1. **Backend unit tests**: Implement tests using `pytest` to verify the multiplication logic.
2. **API contract tests**: Use `pytest` with FastAPI TestClient to validate the endpoint's response format and correctness.

## Rollback/Safety
- If any issues arise during implementation, revert to the last stable commit before the changes.
- Ensure all tests pass before merging the changes.

---

_Spec upgraded by manager: 2023-10-05T12:00:00Z_