# Task: Add support for adding 3 numbers (API + web UI)

## Context
The current implementation of the Number-adder application supports the addition of 2 numbers. This task aims to extend the functionality to allow the addition of 3 numbers while maintaining consistency in the web UI.

## Scope
- **Backend API**: Modify the existing addition endpoint to accept either 2 or 3 numbers.
- **Web UI**: Update the user interface to always display 3 input fields for number addition.

## Non-goals
- Do not alter existing functionality for adding 2 numbers.
- Avoid changes to multiplication or authentication flows.

## Acceptance Criteria (testable)
- [ ] The API accepts requests with either 2 or 3 numbers and returns the correct sum.
- [ ] Existing clients that use the 2-number addition continue to function without changes.
- [ ] The web UI consistently displays 3 input fields for number addition.
- [ ] The submission of the web form sends all three input values.
- [ ] Unit tests are added/updated to cover both 2-number and 3-number addition scenarios using pytest.

## Implementation Notes
- Extend the existing request schema to include an optional third number instead of creating a new endpoint.
- Ensure that any changes made do not interfere with existing functionalities.

## Test Plan
1. **Backend Unit Tests**: Validate business logic for both 2-number and 3-number addition.
2. **Backend API Contract Tests**: Ensure the API responds correctly for both 2-number and 3-number requests.
3. **Frontend Component Tests**: Verify that the UI displays 3 input fields and submits all values correctly.

## Rollback/Safety
- If any issues arise during testing, revert changes to the last stable commit.
- Ensure that all existing tests pass before merging the changes.

---

_Spec upgraded by manager: 2026-02-17T04:26:20+00:00_