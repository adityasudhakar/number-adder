#!/usr/bin/env bash
set -euo pipefail

# Sanitized worker script template.
# Purpose:
# - Claim an issue labeled agent:build
# - Implement changes (via your coding agent)
# - Run tests
# - Push a branch and open a PR

REPO=${REPO:?missing REPO}
WORKER_ID=${WORKER_ID:?missing WORKER_ID}
DEFAULT_BRANCH=${DEFAULT_BRANCH:-master}

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [worker/$WORKER_ID] $*"; }

pick_build_issue() {
  gh issue list --repo "$REPO" --label agent:build --state open --limit 20 --json number,labels \
    --jq '[.[] | select((.labels|map(.name)|index("agent:claimed")|not))][0].number // empty'
}

claim_issue() {
  local issue=$1
  gh issue edit "$issue" --repo "$REPO" --add-label agent:claimed
}

create_branch() {
  local issue=$1
  echo "worker/${WORKER_ID}/issue-${issue}"
}

main() {
  log "Starting worker"

  local issue
  issue=$(pick_build_issue || true)
  if [[ -z "${issue:-}" ]]; then
    log "No available issues found"
    exit 0
  fi

  log "Claiming issue #$issue"
  claim_issue "$issue"

  local branch
  branch=$(create_branch "$issue")
  log "Using branch $branch"

  # Real system steps (template):
  # 1) git clone/fetch
  # 2) checkout -b "$branch" origin/$DEFAULT_BRANCH
  # 3) run coding agent to implement
  # 4) pytest
  # 5) git push origin "$branch"
  # 6) gh pr create

  log "(template) Implement + test + PR create here"
}

main "$@"
