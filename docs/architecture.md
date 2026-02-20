# Architecture (Number Adder)

This repo contains two related-but-separate things:

1) **A Python package on PyPI** (`number-adder`)
2) **A hosted HTTP API** (currently deployed on Railway) that exposes endpoints like `/add`, `/history`, etc.

It also hosts the "0human" automation demo (manager/worker agents on GCP) which operates on this repo via GitHub issues/PRs.

## Repo Layout (high level)

- `number_adder/`
  - `server.py` — FastAPI app (API server)
  - `database.py` — persistence layer
  - `cli.py` — *local* CLI for the Python library (adds numbers locally; not the API client)
- `mobile/` — React/Expo mobile client
- `tasks/` — agent task specs (generated from GitHub issues)
- `.github/workflows/` — automation (issue→task spec PR, CI, etc.)

## Deployments

### API Server (Railway)
- Deploys from this GitHub repo.
- Serves OpenAPI spec at `/openapi.json` and docs at `/api-docs`.

## Authentication model (API)

The API currently supports two auth mechanisms:

- **API key**: `X-API-Key: <key>`
  - Intended for normal product actions like `/add`, `/multiply`, `/history`, `/me`, `/me/export`, etc.

- **Bearer token (JWT-style)**: `Authorization: Bearer <token>`
  - Issued by `/register` and `/login` (returns a `Token`).
  - Used for account-level actions like generating/revoking API keys (`/api-key/*`).

Design goal: users authenticate once with username/password (or OAuth) to obtain a bearer token, then mint an API key for ongoing programmatic usage.

## 0human automation (separate infra)

Outside of this repo, we run always-on agents on GCP VMs:

- Manager VM watches GitHub issue labels and upgrades task specs
- Worker VMs claim build tasks, generate patches, run tests, and open PRs

These VMs use GitHub as a control plane via labels (e.g. `agent:ready → agent:build → agent:claimed`).
