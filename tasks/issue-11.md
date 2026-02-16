```markdown
# Task: Backend: Add /version endpoint

## Source
- GitHub Issue: [#11](https://github.com/adityasudhakar/number-adder/issues/11)

## Context
Implement a new API endpoint `/version` that returns the application version from `pyproject.toml` and the current Git SHA if available.

## Scope
- Create the `/version` endpoint in the backend.
- Extract the version from `pyproject.toml`.
- Retrieve the current Git SHA using a suitable method.

## Non-goals
- This task does not include frontend changes or documentation updates.

## Acceptance Criteria
- [ ] The `/version` endpoint returns a JSON response with the following structure:
  ```json
  {
    "version": "<app_version>",
    "git_sha": "<git_sha>"
  }
  ```
- [ ] If the Git SHA is not available, the response should still include the version:
  ```json
  {
    "version": "<app_version>",
    "git_sha": null
  }
  ```
- [ ] The endpoint responds with a 200 status code for successful requests.
- [ ] Unit tests cover the logic for retrieving version and Git SHA.

## Implementation Notes
- Use FastAPI to implement the endpoint.
- Ensure that the version is read from `pyproject.toml` using a library like `toml`.
- Use `subprocess` to get the current Git SHA.

## Test Plan
1. **Backend unit tests**: Validate the logic for reading the version and Git SHA.
2. **Backend API contract tests**: Test the `/version` endpoint for correct response structure and status codes.

## Rollback/Safety
- If the implementation fails, revert the changes in the endpoint file and run tests to ensure stability.
- Ensure that the new endpoint does not interfere with existing functionality.

---

_Spec upgraded by manager: 2023-10-01T12:00:00Z_
```