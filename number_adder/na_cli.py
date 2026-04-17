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

import ssl
import urllib.error
import urllib.parse
import urllib.request

import certifi

DEFAULT_BASE_URL = "https://number-adder.com"
DEFAULT_CONFIG_PATH = Path("~/.config/na/config.json").expanduser()


def _ssl_context() -> ssl.SSLContext:
    """Return an SSL context with a known-good CA bundle.

    On some macOS Python builds, the system trust store isn't wired up, leading to
    CERTIFICATE_VERIFY_FAILED. Using certifi fixes that.
    """
    return ssl.create_default_context(cafile=certifi.where())


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


def _get_bearer_token(args_token: str | None) -> str | None:
    if args_token:
        return args_token.strip()
    if os.environ.get("NA_ACCESS_TOKEN"):
        return os.environ["NA_ACCESS_TOKEN"].strip()
    cfg = _load_config()
    v = cfg.get("access_token")
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

    if key not in {"api_key", "base_url", "access_token"}:
        print(f"Unsupported config key: {key}", file=sys.stderr)
        return 2

    cfg[key] = value
    _write_config(cfg, path)
    return 0


def _request_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    data: Any | None = None,
    timeout: float = 30.0,
) -> tuple[int, str, dict[str, Any] | str]:
    h = headers or {}
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, method=method.upper(), headers=h, data=body_bytes)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            status = int(getattr(resp, "status", 200))
            raw = resp.read()
            ct = resp.headers.get("content-type", "") or ""
        txt = raw.decode("utf-8", errors="replace")
        if "application/json" in ct and txt:
            return status, ct, json.loads(txt)
        return status, ct, txt
    except urllib.error.HTTPError as e:
        raw = e.read() if hasattr(e, "read") else b""
        txt = raw.decode("utf-8", errors="replace")
        try:
            obj = json.loads(txt) if txt else {"detail": str(e)}
            return int(getattr(e, "code", 500) or 500), "application/json", obj
        except Exception:
            return int(getattr(e, "code", 500) or 500), "text/plain", txt or str(e)


def cmd_auth_register(args: argparse.Namespace) -> int:
    base_url = _get_base_url(args.base_url)
    url = f"{base_url}/register"
    status, _, out = _request_json(
        method="POST",
        url=url,
        data={"email": args.email, "password": args.password},
        timeout=30.0,
    )
    if status >= 200 and status < 300:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    print(json.dumps(out, indent=2, sort_keys=True) if isinstance(out, dict) else str(out), file=sys.stderr)
    return 1


def cmd_auth_login(args: argparse.Namespace) -> int:
    base_url = _get_base_url(args.base_url)
    url = f"{base_url}/login"
    status, _, out = _request_json(
        method="POST",
        url=url,
        data={"email": args.email, "password": args.password},
        timeout=30.0,
    )
    if not (status >= 200 and status < 300) or not isinstance(out, dict):
        print(json.dumps(out, indent=2, sort_keys=True) if isinstance(out, dict) else str(out), file=sys.stderr)
        return 1

    token = out.get("access_token")
    if not token:
        print(json.dumps(out, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    path = Path(args.config_path).expanduser() if args.config_path else DEFAULT_CONFIG_PATH
    cfg = _load_config(path)
    cfg["access_token"] = token
    _write_config(cfg, path)
    print(json.dumps({"ok": True, "saved": str(path), "token_type": out.get("token_type", "bearer")}, indent=2))
    return 0


def cmd_auth_logout(args: argparse.Namespace) -> int:
    path = Path(args.config_path).expanduser() if args.config_path else DEFAULT_CONFIG_PATH
    cfg = _load_config(path)
    cfg.pop("access_token", None)
    _write_config(cfg, path)
    print(json.dumps({"ok": True, "cleared": "access_token", "path": str(path)}, indent=2))
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    method = args.method.upper()
    path = args.path
    if not path.startswith("/"):
        path = "/" + path

    base_url = _get_base_url(args.base_url)
    api_key = _get_api_key(args.api_key)
    bearer = _get_bearer_token(args.access_token)

    if _is_destructive(method) and not args.yes_really:
        print(
            f"Refusing to run {method} without --yes-really (safety).",
            file=sys.stderr,
        )
        return 2

    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

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

        with urllib.request.urlopen(req, timeout=float(args.timeout), context=_ssl_context()) as resp:
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
    p_call.add_argument("--access-token", default=None, help="Bearer access token override (else NA_ACCESS_TOKEN/config)")
    p_call.add_argument("--yes-really", action="store_true", help="Required for DELETE/PUT/PATCH")
    p_call.set_defaults(func=cmd_call)

    # config
    p_cfg = sub.add_parser("config", help="Manage local config (~/.config/na/config.json)")
    cfg_sub = p_cfg.add_subparsers(dest="cfg_cmd", required=True)

    p_show = cfg_sub.add_parser("show", help="Show config")
    p_show.add_argument("--config-path", default=None, help="Override config file path")
    p_show.set_defaults(func=cmd_config_show)

    p_set = cfg_sub.add_parser("set", help="Set config key")
    p_set.add_argument("key", help="api_key|base_url|access_token")
    p_set.add_argument("value", help="Value")
    p_set.add_argument("--config-path", default=None, help="Override config file path")
    p_set.set_defaults(func=cmd_config_set)

    # auth (no browser required)
    p_auth = sub.add_parser("auth", help="Register/login without a browser")
    auth_sub = p_auth.add_subparsers(dest="auth_cmd", required=True)

    p_reg = auth_sub.add_parser("register", help="Create an account (email+password)")
    p_reg.add_argument("email")
    p_reg.add_argument("password")
    p_reg.add_argument("--base-url", default=None)
    p_reg.set_defaults(func=cmd_auth_register)

    p_login = auth_sub.add_parser("login", help="Login (email+password); saves access_token to config")
    p_login.add_argument("email")
    p_login.add_argument("password")
    p_login.add_argument("--base-url", default=None)
    p_login.add_argument("--config-path", default=None)
    p_login.set_defaults(func=cmd_auth_login)

    p_logout = auth_sub.add_parser("logout", help="Clear saved access_token")
    p_logout.add_argument("--config-path", default=None)
    p_logout.set_defaults(func=cmd_auth_logout)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = int(args.func(args))
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
