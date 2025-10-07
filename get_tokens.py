"""
get_tokens.py — Obtain Twitch user access tokens via Device Code flow
and save them into resources/appSettings.env (preserving existing values).

Usage:
    python get_tokens.py

What it does:
    1) Reads/initializes ./resources/appSettings.env
    2) Starts Twitch Device Authorization flow
    3) Polls for the user access token (and refresh token if returned)
    4) Writes/updates values in appSettings.env

Notes:
    - This script overwrites the env file (unknown keys are preserved),
      but comments/ordering (beyond known keys) are not preserved.
    - A .bak backup is created before writing.
"""

from __future__ import annotations

import sys
import time
import webbrowser
from pathlib import Path
from typing import Dict

import requests

ENV_FILE = Path("./resources/appSettings.env")

# Endpoints & constants
DEVICE_CODE_URL = "https://id.twitch.tv/oauth2/device"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"

# Keys we expect in appSettings.env (with defaults for non-secrets)
DEFAULT_KEYS: Dict[str, str] = {
    "OPENAI_API_KEY": "",
    "TWITCH_ACCESS_TOKEN": "",
    "TWITCH_REFRESH_TOKEN": "",
    "TWITCH_CLIENT_ID": "",
    "TWITCH_CLIENT_SECRET": "",
    "TWITCH_BOT_ID": "",
    "PREFIX": "$",
    "INITIAL_CHANNELS": "riotgames",
    "LOG_DIRECTORY": "C:/twitch_logs",
}


def _mask(value: str, keep: int = 12) -> str:
    """Return a masked version of a secret for logging."""
    value = value or ""
    if len(value) <= keep:
        return value[:keep] + "…"
    return value[:keep] + "…"


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE env file into a dict (ignores comments/blank lines)."""
    env: Dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def write_env_file(path: Path, env: Dict[str, str]) -> None:
    """Write env values back to file.

    - Known keys are written first in a stable order (from DEFAULT_KEYS).
    - Unknown keys are appended (preserved).
    - Creates a .bak backup if the file already exists.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Backup
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"📦 Backed up existing env to {backup}")

    # Keep a stable order for readability
    ordered: Dict[str, str] = {
        k: env.get(k, DEFAULT_KEYS.get(k, "")) for k in DEFAULT_KEYS
    }
    # Include any extra unknown keys at the end (preserve user additions)
    for k, v in env.items():
        if k not in ordered:
            ordered[k] = v

    with path.open("w", encoding="utf-8") as f:
        for k, v in ordered.items():
            f.write(f"{k}={v}\n")

    print(f"✅ Updated {path}")


def main() -> None:
    # Load/initialize env file
    env = parse_env_file(ENV_FILE)
    for k, default in DEFAULT_KEYS.items():
        env.setdefault(k, default)

    client_id = env.get("TWITCH_CLIENT_ID", "").strip()
    if not client_id:
        print("❌ Missing TWITCH_CLIENT_ID in resources/appSettings.env")
        print(
            "   → Open resources/appSettings.env and set TWITCH_CLIENT_ID=your_client_id"
        )
        sys.exit(1)

    # Twitch device flow scopes (space-separated). Keep as-is if this worked for you.
    scopes = ["chat:read", "chat:edit", "user:read:chat", "user:write:chat"]

    # Step 1: Request device code
    try:
        r = requests.post(
            DEVICE_CODE_URL,
            data={"client_id": client_id, "scopes": " ".join(scopes)},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to request device code: {e}")
        sys.exit(1)

    resp = r.json()
    device_code = resp["device_code"]
    user_code = resp["user_code"]
    verification_uri = resp["verification_uri"]
    verification_uri_complete = resp.get("verification_uri_complete")
    interval = int(resp.get("interval", 5))
    expires_in = int(resp.get("expires_in", 900))  # default ~15 minutes

    print("==== Twitch Device Authorization ====")
    if verification_uri_complete:
        print(f"Open: {verification_uri_complete}")
    else:
        print(f"Go to {verification_uri} and enter code: {user_code}")

    # Try opening the browser for convenience (ignore failures)
    with suppress_exceptions():
        webbrowser.open(verification_uri_complete or verification_uri, new=2)

    input("Press Enter here AFTER you authorize the app in the browser... ")

    # Step 2: Poll for token (respect interval/expiry)
    start = time.time()
    next_interval = interval

    print("Polling Twitch for tokens…")
    while True:
        # Check expiry window
        if time.time() - start > expires_in:
            print("❌ Authorization window expired. Please run the script again.")
            sys.exit(1)

        try:
            poll = requests.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"\n⚠️ Network error: {e}. Retrying in {next_interval}s…")
            time.sleep(next_interval)
            continue

        if poll.status_code == 200:
            tokens = poll.json()
            env["TWITCH_ACCESS_TOKEN"] = tokens.get("access_token", "")
            env["TWITCH_REFRESH_TOKEN"] = tokens.get("refresh_token", "")

            print("\n✅ Success! Tokens received.")
            if env["TWITCH_ACCESS_TOKEN"]:
                print(f"Access Token:  {_mask(env['TWITCH_ACCESS_TOKEN'])}")
            if env["TWITCH_REFRESH_TOKEN"]:
                print(f"Refresh Token: {_mask(env['TWITCH_REFRESH_TOKEN'])}")

            write_env_file(ENV_FILE, env)
            break

        # Handle expected interim errors from device flow
        error_type = _extract_error(poll)
        if "authorization_pending" in error_type:
            time.sleep(next_interval)
            continue
        if "slow_down" in error_type:
            next_interval += 5
            time.sleep(next_interval)
            continue
        if "expired_token" in error_type or "access_denied" in error_type:
            print(f"❌ {error_type}. Please run the script again.")
            sys.exit(1)

        # Unexpected error
        print(f"❌ Error polling token: {error_type}")
        sys.exit(1)


def _extract_error(resp: requests.Response) -> str:
    """Best-effort device-flow error extractor for non-200 responses."""
    try:
        data = resp.json()
        return str(data.get("error") or data.get("message") or data)
    except Exception:
        return f"HTTP {resp.status_code}"


class suppress_exceptions:
    """Context manager that swallows all exceptions (used for best-effort ops)."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return True  # swallow


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
