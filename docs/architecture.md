# Architecture (Number Adder)

This repo contains three related artifacts:

1) **Python package on PyPI**: `number-adder` (primarily the self-hosted server)
2) **Hosted HTTP API**: calculator-scoped SaaS endpoints
3) **Agent-first API CLI**: `na` (thin generic API caller; uses `X-API-Key`)

It also hosts the "0human" automation demo (manager/worker agents on GCP) which operates on this repo via GitHub issues/PRs.

## Repo Layout (high level)

- `number_adder/`
  - `server.py` — FastAPI app (API server)
  - `database.py` — persistence layer
  - `na_cli.py` — thin CLI wrapper over the hosted API
- `mobile/` — React/Expo mobile client
- `tasks/` — agent task specs (generated from GitHub issues)
- `.github/workflows/` — automation (issue→task spec PR, CI, etc.)

## Deployments

### API Server
- Deploys from this GitHub repo.
- Serves OpenAPI spec at `/openapi.json` and docs at `/api-docs`.

## Authentication model (API)

The API currently supports two auth mechanisms:

- **API key**: `X-API-Key: <key>`
  - Intended for normal product actions.
  - Primary multi-tenant usage is calculator-scoped, e.g. `/calculators/{calc_id}/add` and `/calculators/{calc_id}/history`.

- **Bearer token (JWT-style)**: `Authorization: Bearer <token>`
  - Issued by `/register` and `/login` (returns a `Token`).
  - Used for account-level actions like generating/revoking API keys (`/api-key/*`).

Design goal: users authenticate once with username/password (or OAuth) to obtain a bearer token, then mint an API key for ongoing programmatic usage. The user identity determines which organizations and calculators the caller can access.

## 0human automation (separate infra)

Outside of this repo, we run always-on agents on GCP VMs:

- Manager VM watches GitHub issue labels and upgrades task specs
- Worker VMs claim build tasks, generate patches, run tests, and open PRs

These VMs use GitHub as a control plane via labels (e.g. `agent:ready → agent:build → agent:claimed`).
