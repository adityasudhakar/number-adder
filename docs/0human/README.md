# 0human v2 (public, sanitized)

This directory documents how we run a **human-free** (a.k.a. “0human”) GitHub Issues → PRs → tests → merge loop using a **manager** VM and multiple **worker** VMs.

It’s intentionally **sanitized**:
- No cloud credentials
- No LLM API keys
- No personal tokens
- No OAuth client secrets

You should be able to replicate the architecture with your own infra + keys.

## What this system does

1. You create GitHub Issues with a label like `agent:triage`.
2. A **manager** process:
   - Enriches the issue into a clear spec
   - Flips it to `agent:build`
   - Later reviews worker PRs with deterministic gates (tests, diff allowlist, etc.)
3. **Workers** pick up `agent:build` issues, implement changes (via your coding agent of choice), run tests, push branches, and open PRs.
4. The **manager** merges PRs that pass gates and closes the corresponding issue.

## High-level architecture

- **GitHub** is the control plane (labels = state machine)
- **Manager VM** runs `ohuman-manager.service`
- **Worker VMs** run `ohuman-worker.service` (one per worker)
- Secrets live on the VMs in `/etc/default/ohuman-*` (not in git)

## Safety model (recommended defaults)

Deterministic gates should be the source of truth:
- Only allow changes in a small set of paths (example allowlist)
- Require tests to pass (`pytest`)
- Require PR branch to be up-to-date with base
- Never print secrets in logs

## Files in this folder

- `systemd/` — unit file templates
- `scripts/` — example manager + worker scripts (sanitized)
- `CONFIG.example.env` — environment variables you must provide (placeholders)

## Setup checklist (bring your own secrets)

1. Provision 1 manager VM + N worker VMs.
2. Install:
   - `git`, `gh` (GitHub CLI)
   - Python 3.11+
   - Node (if your agent tooling requires it)
   - your coding agent CLI (Codex / Claude Code / etc.)
3. Put secrets on each VM:
   - `/etc/default/ohuman-manager`
   - `/etc/default/ohuman-worker`
4. Install and enable systemd units from `systemd/`.
5. Create repo labels: `agent:triage`, `agent:build`, `agent:claimed`, `agent:blocked`.
6. Create an issue with `agent:triage`.

## Notes

- If you’re building a public template, consider moving *all* cloud interaction behind GitHub Actions (wake/sleep) and keeping the VMs “dumb”.
- If you need stronger guarantees, add branch protection rules + required checks.
