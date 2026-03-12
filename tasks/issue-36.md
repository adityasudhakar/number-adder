# Task: Show version in footer

## Source
- GitHub Issue: https://github.com/adityasudhakar/number-adder/issues/36

## Context
## Problem
The web UI does not expose the currently deployed app version, so users and developers cannot easily confirm what release is running in production or compare the hosted UI against package/API behavior. This creates friction when debugging, validating deployments, or reporting issues. The backend already exposes version metadata at `/version`, but the frontend is not using it.

## Solution
Add a small client-side version display in the footer of the web UI, sourcing the value from the existing `/version` endpoint. On page load, fetch `/version`, read the `version` field, and render it in the footer as `vX.Y.Z`. If the request fails or returns unexpected data, fail gracefully by either showing a neutral fallback like `version unavailable` or leaving the element hidden.

Keep the change minimal and localized to the static frontend. Primary target is `index.html`; `docs.html` may also be updated if it already shares a similar footer pattern and the change remains low-risk.

## Acceptance Criteria
- [ ] The main web UI (`number_adder/static/index.html`) displays the app version in the footer after the page loads.
- [ ] The displayed format uses the `version` value from `GET /version`, rendered as `v<version>` (example: `v0.3.0`).
- [ ] Version data is fetched client-side from the existing `/version` endpoint; no new backend endpoint is introduced.
- [ ] If the `/version` request fails, returns non-OK, or does not include a usable `version` field, the UI fails gracefully:
  - [ ] either displays `version unavailable`, or
  - [ ] hides/omits the version text without breaking layout or causing visible JS errors.
- [ ] The page remains functional and visually intact whether the version fetch succeeds or fails.
- [ ] Keep the implementation minimal, with changes likely limited to:
  - [ ] `number_adder/static/index.html`
  - [ ] optionally `number_adder/static/docs.html` if applying the same footer treatment there is straightforward
- [ ] Existing tests continue to pass.
- [ ] Add or update tests only if there is already a lightweight pattern for validating static HTML content or version-related behavior; avoid introducing heavy frontend test infrastructure for this change.

## Implementation Hints
- The backend already exposes `/version` and there is an existing version test in `tests/test_version.py`; use that as confirmation of the response shape.
- Static pages live under `number_adder/static/`. The likely simplest approach is:
  - add a footer placeholder element in `index.html`
  - add a small inline script or minimal JS snippet to fetch `/version` and populate the placeholder
- Keep the script defensive:
  - check `response.ok`
  - guard JSON parsing/use of `data.version`
  - avoid throwing uncaught errors
- Match the existing styling/markup conventions in the static pages rather than introducing a new asset pipeline or shared JS file unless one already exists.
- If updating `docs.html` too, do so only if it has a comparable footer structure and the diff stays small.

## Notes
- Non-goal: changing the `/version` API contract or exposing `git_sha` in the footer.
- Non-goal: adding a broader frontend framework, bundling step, or shared client library.
- Keep the diff minimal and focused on surfacing existing backend data in the static UI.
- Prefer graceful degradation over perfect UX if the version endpoint is temporarily unavailable.

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
