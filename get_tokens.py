#!/usr/bin/env python3
"""
get_tokens.py — Obtain Twitch user access tokens via Device Code flow
and save them into resources/appSettings.env (preserving existing values).

Run manually when you need fresh tokens.
"""

import os
import sys
import time
import requests
import webbrowser
from pathlib import Path

ENV_FILE = Path("./resources/appSettings.env")

# Keys we expect in appSettings.env (with defaults for non-secrets)
DEFAULT_KEYS = {
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

def parse_env_file(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def write_env_file(path: Path, env: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep a stable order for readability
    ordered = {k: env.get(k, DEFAULT_KEYS.get(k, "")) for k in DEFAULT_KEYS.keys()}
    # Include any extra unknown keys at the end (preserve user additions)
    for k, v in env.items():
        if k not in ordered:
            ordered[k] = v
    with path.open("w", encoding="utf-8") as f:
        for k, v in ordered.items():
            f.write(f"{k}={v}\n")
    print(f"✅ Updated {path}")

def main():
    # Load/initialize env file
    env = parse_env_file(ENV_FILE)
    for k, default in DEFAULT_KEYS.items():
        env.setdefault(k, default)

    client_id = env.get("TWITCH_CLIENT_ID", "").strip()
    if not client_id:
        print("❌ Missing TWITCH_CLIENT_ID in resources/appSettings.env")
        print("   → Open resources/appSettings.env and set TWITCH_CLIENT_ID=your_client_id")
        sys.exit(1)

    scopes = ["chat:read", "chat:edit", "user:read:chat", "user:write:chat"]

    # Step 1: Request device code
    r = requests.post(
        "https://id.twitch.tv/oauth2/device",
        data={"client_id": client_id, "scopes": " ".join(scopes)},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    r.raise_for_status()
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

    # Try opening the browser for convenience
    try:
        webbrowser.open(verification_uri_complete or verification_uri, new=2)
    except Exception:
        pass

    # Let the user complete authorization first
    input("Press Enter here AFTER you authorize the app in the browser... ")

    # Step 2: Poll for token (respect interval/expiry)
    token_url = "https://id.twitch.tv/oauth2/token"
    start = time.time()
    next_interval = interval

    print("Polling Twitch for tokens...")
    while True:
        # Check expiry window
        if time.time() - start > expires_in:
            print("❌ Authorization window expired. Please run the script again.")
            sys.exit(1)

        try:
            poll = requests.post(
                token_url,
                data={
                    "client_id": client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"\n⚠️ Network error: {e}. Retrying in {next_interval}s...")
            time.sleep(next_interval)
            continue

        if poll.status_code == 200:
            tokens = poll.json()
            env["TWITCH_ACCESS_TOKEN"] = tokens["access_token"]
            env["TWITCH_REFRESH_TOKEN"] = tokens.get("refresh_token", "")

            print("\n✅ Success! Tokens received.")
            print(f"Access Token (truncated): {env['TWITCH_ACCESS_TOKEN'][:12]}...")
            if env["TWITCH_REFRESH_TOKEN"]:
                print(f"Refresh Token (truncated): {env['TWITCH_REFRESH_TOKEN'][:12]}...")

            write_env_file(ENV_FILE, env)
            break
        else:
            # Expected interim errors from device flow
            try:
                err = poll.json()
                error_type = err.get("error") or err.get("message") or str(err)
            except Exception:
                error_type = f"HTTP {poll.status_code}"

            if "authorization_pending" in str(error_type):
                # User hasn't completed approval yet; wait and try again
                time.sleep(next_interval)
                continue
            if "slow_down" in str(error_type):
                # Increase polling interval per spec
                next_interval += 5
                time.sleep(next_interval)
                continue
            if "expired_token" in str(error_type) or "access_denied" in str(error_type):
                print(f"❌ {error_type}. Please run the script again.")
                sys.exit(1)

            # Unexpected error
            print(f"❌ Error polling token: {error_type}")
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
