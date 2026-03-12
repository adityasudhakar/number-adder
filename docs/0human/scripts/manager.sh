#!/usr/bin/env bash
set -euo pipefail

# Sanitized manager script template.
# Purpose:
# - Triage issues with label agent:triage → produce a clearer spec → label agent:build
# - Review worker PRs and merge when deterministic gates pass

REPO=${REPO:?missing REPO}
DEFAULT_BRANCH=${DEFAULT_BRANCH:-master}

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [manager] $*"; }

# Example: pick the oldest triage issue
pick_triage_issue() {
  gh issue list --repo "$REPO" --label agent:triage --state open --limit 1 --json number --jq '.[0].number // empty'
}

triage_issue() {
  local issue=$1
  log "Triaging issue #$issue"

  # In your real system, you’d generate a spec file and post it as a comment.
  gh issue comment "$issue" --repo "$REPO" --body "(sanitized template) Manager triaged this issue and marked it ready for build."
  gh issue edit "$issue" --repo "$REPO" --add-label agent:build --remove-label agent:triage
}

# Deterministic PR gates (examples)
pr_is_up_to_date() {
  local pr=$1
  local base_sha head_sha
  base_sha=$(gh pr view "$pr" --repo "$REPO" --json baseRefOid --jq .baseRefOid)
  head_sha=$(gh pr view "$pr" --repo "$REPO" --json headRefOid --jq .headRefOid)
  # real check should compare merge base; this is just a placeholder
  [[ -n "$base_sha" && -n "$head_sha" ]]
}

run_tests() {
  # In the real system, create a worktree, install deps, run pytest.
  log "(template) running tests..."
}

merge_pr() {
  local pr=$1
  log "Merging PR #$pr"
  gh pr merge "$pr" --repo "$REPO" --merge --delete-branch
}

main() {
  log "Starting manager"

  local issue
  issue=$(pick_triage_issue || true)
  if [[ -n "${issue:-}" ]]; then
    triage_issue "$issue"
  else
    log "No issues need triage"
  fi

  # In real system: iterate open worker PRs and apply gates.
  log "Done"
}

main "$@"
