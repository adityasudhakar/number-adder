# Agent Quickstart (Number Adder)

Goal: an agent should be able to discover how to use Number Adder without needing an interactive browser login.

## Hosted API (Railway)

- Base URL: `https://number-adder.com`
- OpenAPI spec: `https://number-adder.com/openapi.json`
- Docs UI: `https://number-adder.com/api-docs`

### Auth

Most endpoints accept an API key header:

- `X-API-Key: <key>`

(For agent-first usage, prefer API keys over interactive login.)

## Agent-first CLI (na)

The repo includes a generic API caller CLI intended for agents:

- Command: `na`
- Implementation: `number_adder/na_cli.py`

### Install

If you have this repo checked out:

```bash
python -m pip install -e .
```

### Configure auth

Provide the API key via env var:

```bash
export NA_API_KEY="na_..."
```

### Call calculator-scoped endpoints

The primary product API is calculator-scoped. In practice that means:

- authenticate as a user via API key
- choose a calculator the user already has access to
- call endpoints under `/calculators/{calc_id}/...`

```bash
na call GET /calculators --pretty
na call POST /calculators/123/add --data '{"a":2,"b":3}' --pretty
na call GET /calculators/123/history --pretty
```

### Legacy endpoints

Older endpoints like `/add` and `/history` still exist for backward compatibility, but they are no longer the primary model for multi-tenant usage.

```bash
na call GET /version --pretty
na call POST /add --data '{"a":2,"b":3}' --pretty
```

### Safety

Destructive methods require an explicit flag:

```bash
na call DELETE /me --yes-really
```
