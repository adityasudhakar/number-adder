"""Agent-first CLI for the hosted Number Adder API.

Design goals:
- Covers all API paths via a generic `call` command.
- Auth via API key header: X-API-Key.
- Supports env vars + optional config file.

Env vars:
- NA_API_KEY: API key value (preferred for agents)
- NA_BASE_URL: override base URL

Config file (optional):
- ~/.config/na/config.json
  {"api_key": "na_...", "base_url": "https://..."}

"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://number-adder.com"
DEFAULT_CONFIG_PATH = Path("~/.config/na/config.json").expanduser()


def _load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Never crash on config parse; just behave as if empty.
        return {}


def _write_config(cfg: dict[str, Any], path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Best-effort permissions hardening.
    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except Exception:
        pass
    tmp.replace(path)


def _get_base_url(args_base_url: str | None) -> str:
    if args_base_url:
        return args_base_url.rstrip("/")
    if os.environ.get("NA_BASE_URL"):
        return os.environ["NA_BASE_URL"].rstrip("/")
    cfg = _load_config()
    if isinstance(cfg.get("base_url"), str) and cfg["base_url"].strip():
        return str(cfg["base_url"]).rstrip("/")
    return DEFAULT_BASE_URL


def _get_api_key(args_api_key: str | None) -> str | None:
    if args_api_key:
        return args_api_key.strip()
    if os.environ.get("NA_API_KEY"):
        return os.environ["NA_API_KEY"].strip()
    cfg = _load_config()
    v = cfg.get("api_key")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _is_destructive(method: str) -> bool:
    return method.upper() in {"DELETE", "PUT", "PATCH"}


def cmd_config_show(args: argparse.Namespace) -> int:
    cfg = _load_config(Path(args.config_path).expanduser() if args.config_path else DEFAULT_CONFIG_PATH)
    print(json.dumps(cfg, indent=2, sort_keys=True))
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    path = Path(args.config_path).expanduser() if args.config_path else DEFAULT_CONFIG_PATH
    cfg = _load_config(path)

    key = args.key
    value = args.value

    if key not in {"api_key", "base_url"}:
        print(f"Unsupported config key: {key}", file=sys.stderr)
        return 2

    cfg[key] = value
    _write_config(cfg, path)
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    method = args.method.upper()
    path = args.path
    if not path.startswith("/"):
        path = "/" + path

    base_url = _get_base_url(args.base_url)
    api_key = _get_api_key(args.api_key)

    if _is_destructive(method) and not args.yes_really:
        print(
            f"Refusing to run {method} without --yes-really (safety).",
            file=sys.stderr,
        )
        return 2

    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key

    # Parse query params: --query k=v (repeatable)
    params: list[tuple[str, str]] = []
    for q in args.query or []:
        if "=" not in q:
            print(f"Bad --query value (expected k=v): {q}", file=sys.stderr)
            return 2
        k, v = q.split("=", 1)
        params.append((k, v))

    data: Any | None = None
    if args.data_file:
        p = Path(args.data_file)
        data = json.loads(p.read_text(encoding="utf-8"))
    elif args.data:
        data = json.loads(args.data)

    url = f"{base_url}{path}"

    try:
        # Build URL with query string
        if params:
            parsed = urllib.parse.urlparse(url)
            q = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            q.extend(params)
            url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(q)))

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url=url, method=method, headers=headers, data=body_bytes)

        with urllib.request.urlopen(req, timeout=float(args.timeout)) as resp:
            status = int(getattr(resp, "status", 200))
            raw = resp.read()
            ct = resp.headers.get("content-type", "") or ""

        if status < 200 or status >= 300:
            # Should mostly be handled by HTTPError, but keep a fallback.
            print(raw.decode("utf-8", errors="replace"), file=sys.stderr)
            return 1

        if "application/json" in ct:
            obj = json.loads(raw.decode("utf-8")) if raw else {}
            print(json.dumps(obj, indent=2 if args.pretty else None, sort_keys=True))
        else:
            print(raw.decode("utf-8", errors="replace"))
        return 0

    except urllib.error.HTTPError as e:
        try:
            raw = e.read()
            # Try to pretty-print JSON errors
            try:
                obj = json.loads(raw.decode("utf-8")) if raw else {"detail": str(e)}
                print(json.dumps(obj, indent=2 if args.pretty else None, sort_keys=True), file=sys.stderr)
            except Exception:
                print(raw.decode("utf-8", errors="replace"), file=sys.stderr)
        except Exception:
            print(str(e), file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="na", description="Agent-first CLI for Number Adder API")
    sub = p.add_subparsers(dest="cmd", required=True)

    # call
    p_call = sub.add_parser("call", help="Call any API path")
    p_call.add_argument("method", help="HTTP method (GET/POST/...)" )
    p_call.add_argument("path", help="Path like /add")
    p_call.add_argument("--base-url", default=None, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    p_call.add_argument("--api-key", default=None, help="API key override (else NA_API_KEY/config)")
    p_call.add_argument("--query", action="append", default=[], help="Query param k=v (repeatable)")
    p_call.add_argument("--data", default=None, help="JSON body as string")
    p_call.add_argument("--data-file", default=None, help="Path to JSON file for request body")
    p_call.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    p_call.add_argument("--timeout", type=float, default=30.0, help="Request timeout (seconds)")
    p_call.add_argument("--yes-really", action="store_true", help="Required for DELETE/PUT/PATCH")
    p_call.set_defaults(func=cmd_call)

    # config
    p_cfg = sub.add_parser("config", help="Manage local config (~/.config/na/config.json)")
    cfg_sub = p_cfg.add_subparsers(dest="cfg_cmd", required=True)

    p_show = cfg_sub.add_parser("show", help="Show config")
    p_show.add_argument("--config-path", default=None, help="Override config file path")
    p_show.set_defaults(func=cmd_config_show)

    p_set = cfg_sub.add_parser("set", help="Set config key")
    p_set.add_argument("key", help="api_key|base_url")
    p_set.add_argument("value", help="Value")
    p_set.add_argument("--config-path", default=None, help="Override config file path")
    p_set.set_defaults(func=cmd_config_set)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = int(args.func(args))
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
