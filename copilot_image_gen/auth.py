"""
auth.py — Token acquisition for the image generation MCP server.

Flow:
  1. Check for cached refresh token
  2. If found, silently exchange for a new access token (Sydney resource)
  3. If not found (or expired), open a browser for interactive login:
     - Playwright launches Edge (or configured browser) headful
     - User signs in (SSO/MFA as required)
     - Script intercepts the redirect to nativeclient?code=...
     - Exchange auth code for access + refresh tokens
  4. Cache the refresh token for next time (~90 day sliding window)

Targets the Sydney resource (https://substrate.office.com/sydney) for
Copilot image generation via SignalR WebSocket.

Browser config (env vars):
  COPILOT_BROWSER   Browser channel: msedge (default), chrome, chromium
  COPILOT_TENANT    Azure AD tenant (default: common)
"""

import json
import os
import platform
import sys
import urllib.parse
import base64
from pathlib import Path

import requests

from .config import (
    CLIENT_ID,
    SCOPES,
    REDIRECT_URI,
    TOKEN_URL,
    AUTHORIZE_URL,
    DEFAULT_BROWSER,
    get_cache_dir,
)
from .models import AccountInfo


# ── Logging ─────────────────────────────────────────────────────────────────

def _log(msg: str):
    """Print to stderr so we don't corrupt MCP stdio protocol."""
    print(msg, file=sys.stderr, flush=True)


# ── Token cache ─────────────────────────────────────────────────────────────

def _cache_file() -> Path:
    return get_cache_dir() / "token_cache.json"


def _load_cache() -> dict:
    path = _cache_file()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_cache(data: dict):
    path = _cache_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    if os.name != "nt":
        path.chmod(0o600)


# ── Token refresh (silent) ──────────────────────────────────────────────────

def _refresh_token(refresh_token: str) -> dict | None:
    """Exchange a refresh token for a new access + refresh token pair."""
    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": SCOPES,
    }, timeout=15)

    if resp.status_code == 200:
        result = resp.json()
        if "access_token" in result:
            return result
    return None


# ── Auth code exchange ──────────────────────────────────────────────────────

def _exchange_code(code: str) -> dict | None:
    """Exchange an authorization code for tokens."""
    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    }, timeout=15)

    if resp.status_code == 200:
        result = resp.json()
        if "access_token" in result:
            return result

    try:
        err = resp.json()
        _log(f"  Error: Token exchange failed: {err.get('error', resp.status_code)}")
        _log(f"     {err.get('error_description', '')[:200]}")
    except Exception:
        _log(f"  Error: Token exchange failed: HTTP {resp.status_code}")
    return None


# ── Browser-based login (Playwright) ────────────────────────────────────────

def _edge_profile_dir() -> str | None:
    """Return the Edge user data directory if it exists."""
    system = platform.system()
    if system == "Darwin":
        path = Path.home() / "Library" / "Application Support" / "Microsoft Edge"
    elif system == "Windows":
        base = os.environ.get("LOCALAPPDATA", str(Path.home()))
        path = Path(base) / "Microsoft" / "Edge" / "User Data"
    elif system == "Linux":
        path = Path.home() / ".config" / "microsoft-edge"
    else:
        return None
    return str(path) if path.is_dir() else None


def _own_profile_dir() -> str:
    """Our own persistent browser profile directory (fallback)."""
    return str(get_cache_dir() / "browser_profile")


def _browser_login(auth_url: str) -> str | None:
    """Open a real browser via Playwright, intercept the nativeclient redirect."""
    from playwright.sync_api import sync_playwright

    channel = DEFAULT_BROWSER
    captured_code = None
    captured_error = None

    def _on_request(request):
        nonlocal captured_code, captured_error
        url = request.url
        if "nativeclient" not in url:
            return
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            captured_code = params["code"][0]
        elif "error" in params:
            err = params["error"][0]
            desc = params.get("error_description", [""])[0]
            captured_error = f"{err}: {urllib.parse.unquote(desc)}"

    with sync_playwright() as p:
        context = None

        edge_dir = _edge_profile_dir() if channel == "msedge" else None
        profile_dirs = []
        if edge_dir:
            profile_dirs.append(("Edge profile", edge_dir))
        profile_dirs.append(("app profile", _own_profile_dir()))

        for label, user_data_dir in profile_dirs:
            try:
                _log(f"  Trying {label}...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    channel=channel,
                    headless=False,
                    viewport={"width": 500, "height": 700},
                    args=["--disable-blink-features=AutomationControlled"],
                )
                break
            except Exception as e:
                err_msg = str(e)
                if "already" in err_msg.lower() or "lock" in err_msg.lower():
                    _log(f"  {label} is locked (browser running), trying next...")
                    continue
                _log(f"  Warning: {label} failed: {err_msg[:100]}")
                continue

        if context is None:
            _log("  Error: Could not launch browser.")
            _log("  Set COPILOT_BROWSER=chrome or COPILOT_BROWSER=chromium")
            return None

        page = context.pages[0] if context.pages else context.new_page()
        page.on("request", _on_request)
        page.goto(auth_url, wait_until="commit")

        try:
            while captured_code is None and captured_error is None:
                page.wait_for_timeout(300)
        except Exception:
            pass

        try:
            context.close()
        except Exception:
            pass

    if captured_error:
        _log(f"  Error: {captured_error[:200]}")
        return None
    return captured_code


# ── Interactive login ───────────────────────────────────────────────────────

def _interactive_login() -> dict | None:
    """Open browser for login and capture auth code."""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_mode": "query",
    }
    auth_url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)

    channel = DEFAULT_BROWSER
    _log(f"\n  Copilot Image Gen - Sign in required (browser: {channel})")
    _log("  Opening sign-in window...\n")

    code = _browser_login(auth_url)

    if not code:
        _log("  Error: Sign-in was cancelled or failed.")
        return None

    _log("  Exchanging code for token...")
    return _exchange_code(code)


# ── Decode JWT (for info only) ──────────────────────────────────────────────

def decode_jwt(token: str) -> dict:
    """Decode a JWT payload (without verification). For extracting claims."""
    parts = token.split(".")
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


# ── Public API ──────────────────────────────────────────────────────────────

def get_token(silent: bool = False) -> str:
    """Get a valid access token for the Sydney resource.

    Args:
        silent: If True, don't prompt for interactive login (return empty string
                if no cached token is available). Used by MCP server to avoid
                blocking stdin.

    Returns:
        A valid JWT access token, or empty string if auth fails.
    """
    cache = _load_cache()

    # Try refresh token first
    refresh = cache.get("refresh_token")
    if refresh:
        result = _refresh_token(refresh)
        if result:
            _save_cache({
                "refresh_token": result.get("refresh_token", refresh),
                "account": cache.get("account", {}),
            })
            return result["access_token"]

    # No valid refresh token — need interactive login
    if silent:
        return ""

    result = _interactive_login()
    if not result:
        return ""

    # Cache the refresh token and account info
    token = result["access_token"]
    try:
        claims = decode_jwt(token)
        account_data = {
            "name": claims.get("name", ""),
            "upn": claims.get("upn", ""),
            "oid": claims.get("oid", ""),
            "tid": claims.get("tid", ""),
        }
    except Exception:
        account_data = {}

    _save_cache({
        "refresh_token": result.get("refresh_token", ""),
        "account": account_data,
    })

    _log(f"\n  Signed in as {account_data.get('name', 'Unknown')}")
    _log(f"     Token cached at {_cache_file()}")
    return token


def get_cached_account() -> AccountInfo:
    """Return cached account info or empty AccountInfo."""
    cache = _load_cache()
    data = cache.get("account", {})
    return AccountInfo(
        name=data.get("name", ""),
        upn=data.get("upn", ""),
        oid=data.get("oid", ""),
        tid=data.get("tid", ""),
    )


def logout():
    """Clear the cached token."""
    path = _cache_file()
    if path.exists():
        path.unlink()
        _log("  Signed out. Token cache cleared.")
    else:
        _log("  No cached token found.")


# ── CLI entry point (for testing) ───────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "logout":
        logout()
    else:
        token = get_token()
        if token:
            claims = decode_jwt(token)
            print(f"\n  Token acquired:")
            print(f"    aud:   {claims.get('aud', '?')}")
            print(f"    appid: {claims.get('appid', '?')}")
            print(f"    scp:   {claims.get('scp', '?')}")
            print(f"    name:  {claims.get('name', '?')}")
            print(f"    exp:   {claims.get('exp', '?')}")
        else:
            print("  Error: Failed to get token")
            sys.exit(1)
