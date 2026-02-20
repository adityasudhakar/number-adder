# Agent Quickstart (Number Adder)

Goal: an agent should be able to discover how to use Number Adder without needing an interactive browser login.

## Hosted API (Railway)

- Base URL: `https://number-adder.up.railway.app`
- OpenAPI spec: `https://number-adder.up.railway.app/openapi.json`
- Docs UI: `https://number-adder.up.railway.app/api-docs`

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

### Call any endpoint

```bash
na call GET /version --pretty
na call POST /add --data '{"a":2,"b":3}' --pretty
na call GET /history --pretty
```

### Safety

Destructive methods require an explicit flag:

```bash
na call DELETE /me --yes-really
```
