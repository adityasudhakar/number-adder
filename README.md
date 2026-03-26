# Number Adder

<p align="center">
  <img src="number_adder/static/assets/logo.svg" alt="Number Adder logo" width="160" />
</p>

A multi-tenant calculator service with:

- **Hosted API** for organization and calculator-scoped usage
- **Self-hosted server** via PyPI
- **Thin agent-first CLI** (`na`) for calling the hosted API

## Quick links (hosted)

- API base: https://number-adder.com
- OpenAPI: https://number-adder.com/openapi.json
- API docs: https://number-adder.com/api-docs

## Agent Quickstart

See: `docs/agent-quickstart.md`

## Self-hosting via PyPI

### Installation

```bash
pip install number-adder
```

### Run the server

```bash
number-adder-server
```

## Thin API CLI

The package also includes `na`, a thin wrapper around the hosted API for agent and shell usage.
