# bot/twitch_api.py
from __future__ import annotations

import time
from typing import Dict, Tuple

import requests

HELIX = "https://api.twitch.tv/helix"


class TwitchApi:
    """Lightweight wrapper for Twitch Helix REST endpoints used by the chatbot.

    Features:
        • Resolve channel logins → broadcaster IDs
        • Send chat messages
        • Check live state with 15-second caching

    Notes:
        - The access token must include `user:read:email` and `user:write:chat` scopes.
        - All methods raise `requests.HTTPError` for non-2xx responses.
    """

    def __init__(self, client_id: str, access_token: str):
        """Initialize a Twitch API helper.

        Args:
            client_id: Twitch app client ID.
            access_token: OAuth user token (may start with 'oauth:').
        """
        self.client_id = client_id
        self.access_token = access_token.removeprefix("oauth:")
        self._headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        # Cache structure: { broadcaster_id: (is_live_bool, timestamp) }
        self._live_cache: Dict[str, Tuple[bool, float]] = {}

    # ------------------- User Resolution -------------------

    def resolve_logins(self, logins: list[str]) -> dict[str, str]:
        """Resolve a list of Twitch login names to their numeric user IDs.

        Args:
            logins: List of Twitch login names.

        Returns:
            Dictionary mapping login → user_id.
        """
        if not logins:
            return {}
        params = [("login", login) for login in logins]
        r = requests.get(
            f"{HELIX}/users", headers=self._headers, params=params, timeout=15
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        return {u["login"].lower(): u["id"] for u in data}

    # ------------------- Chat Messages -------------------

    def send_message(self, broadcaster_id: str, sender_id: str, message: str) -> dict:
        """Send a chat message via Helix.

        Args:
            broadcaster_id: Channel owner’s user ID.
            sender_id: Bot account’s user ID.
            message: Message text to send.

        Returns:
            Parsed JSON response from Twitch.

        Raises:
            requests.HTTPError: If Twitch returns a non-2xx status.
        """
        payload = {
            "broadcaster_id": str(broadcaster_id),
            "sender_id": str(sender_id),
            "message": message,
        }
        r = requests.post(
            f"{HELIX}/chat/messages", headers=self._headers, json=payload, timeout=15
        )
        if r.status_code >= 400:
            print(f"[twitch_api] SEND ERROR {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()

    # ------------------- Live State -------------------

    def is_live(self, broadcaster_id: str) -> bool:
        """Check whether a channel is currently live, with 15-second caching.

        Args:
            broadcaster_id: Numeric Twitch user ID.

        Returns:
            True if the channel is live, False otherwise.
        """
        now = time.time()
        cached = self._live_cache.get(broadcaster_id)
        if cached and (now - cached[1] < 15):
            return cached[0]

        r = requests.get(
            f"{HELIX}/streams",
            headers=self._headers,
            params={"user_id": broadcaster_id},
            timeout=10,
        )
        r.raise_for_status()
        live = bool(r.json().get("data"))
        self._live_cache[broadcaster_id] = (live, now)
        return live
