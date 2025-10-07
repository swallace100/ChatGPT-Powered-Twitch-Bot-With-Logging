from __future__ import annotations

import asyncio
import datetime
import json
import pathlib
import time
from typing import Dict, Optional

import requests
import websockets

HELIX = "https://api.twitch.tv/helix"
WS_URL = "wss://eventsub.wss.twitch.tv/ws"


class EventSubChatBot:
    """AI-powered Twitch bot that listens via EventSub WebSocket and replies via Helix.

    Responsibilities:
        - Resolve channel logins → broadcaster IDs.
        - Maintain a WebSocket session for EventSub notifications.
        - Subscribe to `channel.chat.message` per configured channel.
        - Log messages and delegate command handling via an injected bridge.
    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        bot_user_id: str,
        channel_logins: list[str],
        log_directory: str = "logs",
        active: bool = True,
        prefixes=("$",),
        suppress_when_live: bool = True,
    ):
        self.client_id = client_id
        self.access_token = access_token.removeprefix("oauth:")
        self.bot_user_id = str(bot_user_id)
        self.channel_logins = channel_logins
        self.log_dir = pathlib.Path(log_directory)
        self.prefixes = (
            tuple(prefixes) if isinstance(prefixes, (list, tuple)) else (prefixes,)
        )
        self._active = active
        self._suppress_when_live = suppress_when_live

        # runtime state
        self._live_cache: Dict[str, tuple[bool, float]] = {}
        self._headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id: Optional[str] = None
        self._sub_ids: Dict[str, str] = {}  # login -> subscription id
        self._login_to_id: Dict[str, str] = {}  # login -> broadcaster user id

    # ---------------- lifecycle ----------------

    async def start(self) -> None:
        """Resolve channels, connect WebSocket, subscribe, and process events."""
        self._resolve_logins_to_ids()
        if not self._login_to_id:
            raise RuntimeError("No valid channels to subscribe to.")
        await self._run_ws_loop()

    async def stop(self) -> None:
        """Close the websocket if open."""
        if self._ws:
            await self._ws.close()
            self._ws = None

    # ---------------- control helpers ----------------

    def get_active(self) -> bool:
        """Return whether the bot is currently active."""
        return self._active

    def set_active(self, status: bool) -> None:
        """Enable/disable the bot’s message handling."""
        self._active = status
        print(f"Active set to {self._active}")

    async def activation_timer(self, seconds: int = 10) -> None:
        """Temporarily disable, then auto-reenable after `seconds`."""
        self.set_active(False)
        await asyncio.sleep(seconds)
        self.set_active(True)

    # ---------------- websocket loop ----------------

    async def _run_ws_loop(self) -> None:
        async with websockets.connect(WS_URL, ping_interval=None) as ws:
            self._ws = ws

            # Expect WELCOME
            frame = json.loads(await ws.recv())
            if frame.get("metadata", {}).get("message_type") != "session_welcome":
                raise RuntimeError(f"Unexpected first message: {frame}")
            self._session_id = frame["payload"]["session"]["id"]
            keepalive = frame["payload"]["session"]["keepalive_timeout_seconds"]
            print(f"WS connected. session={self._session_id} keepalive={keepalive}s")

            # Subscribe per channel (best effort)
            for login in list(self._login_to_id.keys()):
                try:
                    self._subscribe_chat_for(login)
                except Exception as e:
                    print(f"SUBSCRIBE ERROR for {login}: {e}")

            # Main loop
            while True:
                raw = await ws.recv()
                f = json.loads(raw)
                mtype = f.get("metadata", {}).get("message_type")

                if mtype == "session_keepalive":
                    continue
                if mtype == "revocation":
                    print(
                        "Subscription revoked:",
                        f.get("payload", {}).get("subscription"),
                    )
                    continue
                if mtype != "notification":
                    continue

                sub_type = f["payload"]["subscription"]["type"]
                if sub_type == "channel.chat.message":
                    await self._on_chat_message(f["payload"]["event"])

    # ---------------- events ----------------

    async def _on_chat_message(self, event: dict) -> None:
        """Handle a single `channel.chat.message` event."""
        # expected fields:
        #   broadcaster_user_login, broadcaster_user_id
        #   chatter_user_login, chatter_user_id
        #   message: { text, fragments: [...] }
        try:
            channel_login = event["broadcaster_user_login"]
            broadcaster_id = event["broadcaster_user_id"]
            user_login = event["chatter_user_login"]
            text = event["message"]["text"]
        except KeyError as e:
            print(f"[on_chat_message] Missing key in event: {e!s}. Event: {event}")
            return

        print(f"[{channel_login} ({broadcaster_id})] {user_login}: {text}")

        if not self._active:
            return

        self._log_message(channel_login, user_login, text)

        # Delegate to the bridge set in bot.app.build_bot()
        if hasattr(self, "_command_bridge"):
            await self._command_bridge(event)

    # ---------------- REST helpers & utilities ----------------

    def _resolve_logins_to_ids(self) -> None:
        """Populate self._login_to_id from self.channel_logins via Helix /users."""
        if not self.channel_logins:
            self._login_to_id = {}
            return

        params = [("login", login) for login in self.channel_logins]
        r = requests.get(
            f"{HELIX}/users", headers=self._headers, params=params, timeout=15
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        self._login_to_id = {u["login"].lower(): u["id"] for u in data}

        missing = [
            login for login in self.channel_logins if login not in self._login_to_id
        ]
        if missing:
            print(f"⚠️ Could not resolve these logins: {missing}")
        else:
            print(f"Resolved channels: {self._login_to_id}")

    def _subscribe_chat_for(self, login: str) -> None:
        """Create EventSub subscription for `channel.chat.message` for one channel."""
        bid = self._login_to_id.get(login)
        if not bid:
            return
        payload = {
            "type": "channel.chat.message",
            "version": "1",
            "condition": {
                "broadcaster_user_id": str(bid),
                "user_id": str(self.bot_user_id),
            },
            "transport": {"method": "websocket", "session_id": self._session_id},
        }
        r = requests.post(
            f"{HELIX}/eventsub/subscriptions",
            headers=self._headers,
            data=json.dumps(payload),
            timeout=15,
        )
        if r.status_code >= 400:
            print("SUBSCRIBE ERROR", login, r.status_code, r.text)
            r.raise_for_status()
        data = r.json()
        sub_id = data["data"][0]["id"]
        self._sub_ids[login] = sub_id
        print(f"✅ Subscribed to #{login} ({bid})")

    def _log_message(self, channel: str, user: str, text: str) -> None:
        """Append a chat line to logs/<channel>/<YYYY-MM-DD>/<YYYY-MM-DD>.txt."""
        now = datetime.datetime.now()
        date_str = now.date().isoformat()
        time_str = now.strftime("%H:%M:%S")
        path = self.log_dir / channel / date_str
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{date_str}.txt"
        with file_path.open("a", encoding="utf-8") as f:
            f.write(f"{date_str} {time_str} {user}: {text}\n")

    async def _is_channel_live(self, broadcaster_id: str) -> bool:
        """Private live check with a 15s cache (Helix /streams)."""
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
        is_live = bool(r.json().get("data"))
        self._live_cache[broadcaster_id] = (is_live, now)
        return is_live

    # ---- public wrapper for app/handlers ----

    async def is_channel_live(self, broadcaster_id: str) -> bool:
        """Public API: return whether the channel is currently live."""
        return await self._is_channel_live(broadcaster_id)

    def send_message(self, broadcaster_id: str, sender_id: str, message: str):
        """POST /chat/messages (requires user:write:chat)."""
        data = {
            "broadcaster_id": str(broadcaster_id),
            "sender_id": str(sender_id),
            "message": message,
        }
        r = requests.post(
            f"{HELIX}/chat/messages", headers=self._headers, json=data, timeout=15
        )
        if r.status_code >= 400:
            print("SEND ERROR", r.status_code, r.text)
        r.raise_for_status()
        return r.json()
