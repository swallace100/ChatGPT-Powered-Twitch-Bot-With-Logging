import os
import json
import time
import asyncio
import datetime
import pathlib
import websockets
import requests
import random
from openai import OpenAI
from base64 import b64decode
from dotenv import load_dotenv

HELIX = "https://api.twitch.tv/helix"
WS_URL = "wss://eventsub.wss.twitch.tv/ws"


class EventSubChatBot:
    """
    AI-powered Twitch bot using EventSub WebSocket.

    Features:
        - Listens to chat messages via EventSub.
        - Supports commands like $about, $joke, $trivia, $story, $nickname, $touchgrass, $image.
        - Logs chat activity into daily text files.
        - Integrates with OpenAI for generative responses.
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
    ):
        """
        Initialize the chatbot.

        Args:
            client_id (str): Twitch app client ID.
            client_secret (str): Twitch app client secret (optional if device flow).
            token (str): User OAuth token with required scopes.
            bot_id (str): Twitch bot account user ID.
            prefixes (list[str]): Command prefixes (e.g., ['$']).
            channels (dict[str, str]): Mapping of channel login → broadcaster_user_id.
            log_dir (Path): Directory where chat logs are stored.
        """

        # Store config values
        self.client_id = client_id
        self.access_token = access_token.removeprefix("oauth:")
        self.bot_user_id = str(bot_user_id)
        self.channel_logins = channel_logins
        self.log_dir = pathlib.Path(log_directory)
        self.prefixes = (
            tuple(prefixes) if isinstance(prefixes, (list, tuple)) else (prefixes,)
        )
        self._live_cache = {}  # broadcaster_id -> (is_live_bool, timestamp)
        self._active = active

        # ChatGPT output management
        self._recent_jokes = []
        self._recent_stories = []
        self._recent_trivia = []
        self._recent_nicknames = []

        # runtime state
        self._headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        self._ws = None
        self._session_id = None
        self._sub_ids = {}  # login -> subscription id
        self._login_to_id = {}  # login -> numeric id

    # ------------ public control ------------
    def get_active(self) -> bool:
        return self._active

    def set_active(self, status: bool):
        self._active = status
        print(f"Active set to {self._active}")

    async def activation_timer(self, seconds: int = 10):
        """Temporarily disable, then auto-reenable."""
        self.set_active(False)
        await asyncio.sleep(seconds)
        self.set_active(True)

    async def start(self):
        """Resolve channels -> IDs, open WS, subscribe, and listen forever."""
        self._resolve_logins_to_ids()
        if not self._login_to_id:
            raise RuntimeError("No valid channels to subscribe to.")
        await self._run_ws_loop()

    async def stop(self):
        """Close WS and (optionally) delete subs (kept minimal)."""
        if self._ws:
            await self._ws.close()
            self._ws = None

    # ------------ sending messages ------------
    def send_message(self, broadcaster_id: str, message: str):
        """POST /chat/messages (requires scope user:write:chat)."""
        data = {
            "broadcaster_id": str(broadcaster_id),
            "sender_id": self.bot_user_id,
            "message": message,
        }
        r = requests.post(
            f"{HELIX}/chat/messages", headers=self._headers, json=data, timeout=15
        )
        if r.status_code >= 400:
            print("SEND ERROR", r.status_code, r.text)
        r.raise_for_status()
        return r.json()

    # ------------ internals ------------
    def _resolve_logins_to_ids(self):
        if not self.channel_logins:
            return
        params = [("login", login) for login in self.channel_logins]
        r = requests.get(
            f"{HELIX}/users", headers=self._headers, params=params, timeout=15
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        self._login_to_id = {u["login"].lower(): u["id"] for u in data}
        missing = [l for l in self.channel_logins if l not in self._login_to_id]
        if missing:
            print(f"⚠️ Could not resolve these logins: {missing}")
        else:
            print(f"Resolved channels: {self._login_to_id}")

    def _subscribe_chat_for(self, login: str):
        """Create EventSub subscription for channel.chat.message (per channel)."""
        bid = self._login_to_id.get(login)
        if not bid:
            return
        payload = {
            "type": "channel.chat.message",
            "version": "1",
            "condition": {
                "broadcaster_user_id": str(bid),
                "user_id": str(self.bot_user_id),  # your token's user id
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

    async def _run_ws_loop(self):
        async with websockets.connect(WS_URL, ping_interval=None) as ws:
            self._ws = ws
            # Expect WELCOME
            frame = json.loads(await ws.recv())
            if frame.get("metadata", {}).get("message_type") != "session_welcome":
                raise RuntimeError(f"Unexpected first message: {frame}")
            self._session_id = frame["payload"]["session"]["id"]
            keepalive = frame["payload"]["session"]["keepalive_timeout_seconds"]
            print(f"WS connected. session={self._session_id} keepalive={keepalive}s")

            # subscribe per channel
            for login in self._login_to_id.keys():
                self._subscribe_chat_for(login)

            # main loop
            while True:
                raw = await ws.recv()
                frame = json.loads(raw)
                mtype = frame.get("metadata", {}).get("message_type")

                if mtype == "session_keepalive":
                    continue
                if mtype == "revocation":
                    print("Subscription revoked:", frame["payload"]["subscription"])
                    continue
                if mtype != "notification":
                    continue

                sub_type = frame["payload"]["subscription"]["type"]
                event = frame["payload"]["event"]

                if sub_type == "channel.chat.message":
                    self._on_chat_message(event)

    # ------------ event handlers ------------
    def _on_chat_message(self, event: dict):
        # event fields:
        # broadcaster_user_login, broadcaster_user_id
        # chatter_user_login, chatter_user_id
        # message: { text, fragments: [...] }
        channel_login = event["broadcaster_user_login"]
        broadcaster_id = event["broadcaster_user_id"]
        user_login = event["chatter_user_login"]
        text = event["message"]["text"]

        # Console print
        print(f"[{channel_login}] {user_login}: {text}")

        # Skip logging/responding if inactive
        if not self._active:
            return

        # Log to file
        self._log_message(channel_login, user_login, text)

        # Example: simple auto-reply (requires user:write:chat)
        # if text.strip() == "$ping":
        #     self.send_message(event["broadcaster_user_id"], "pong")

        # Command check
        if not text:
            return
        if not any(text.startswith(p) for p in self.prefixes):
            return

        # parse: $cmd rest...
        prefix = next(p for p in self.prefixes if text.startswith(p))
        parts = text[len(prefix) :].strip().split(None, 1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        # dispatch map
        handlers = {
            "about": self.cmd_about,
            "inputs": self.cmd_inputs,
            "joke": self.cmd_joke,
            "nickname": self.cmd_nickname,
            "story": self.cmd_story,
            "touchgrass": self.cmd_touchgrass,
            "trivia": self.cmd_trivia,
            "image": self.cmd_image,
        }

        handler = handlers.get(cmd)
        if not handler:
            return

        # Run the handler (async), catch errors, send reply
        asyncio.create_task(
            self._run_command(handler, broadcaster_id, channel_login, user_login, arg)
        )

    def _log_message(self, channel: str, user: str, text: str):
        now = datetime.datetime.now()
        date_str = now.date().isoformat()
        time_str = now.strftime("%H:%M:%S")
        path = self.log_dir / channel / date_str
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{date_str}.txt"
        with file_path.open("a", encoding="utf-8") as f:
            f.write(f"{date_str} {time_str} {user}: {text}\n")

    async def _run_command(
        self,
        handler,
        broadcaster_id: str,
        channel_login: str,
        user_login: str,
        arg: str,
    ):
        # auto-disable after one command
        try:
            # Skip if channel is live
            if await self._is_channel_live(broadcaster_id):
                print(f"#{channel_login} is live — command suppressed.")
                return

            reply = await handler(user_login, arg)
            if reply:
                self.send_message(broadcaster_id, reply)
                # command cooldown
                await self.activation_timer(10)
        except Exception as e:
            print("Command error:", e)

    # ------------------- LIVE CHECK -------------------
    async def _is_channel_live(self, broadcaster_id: str) -> bool:
        # simple 15s cache
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

    # ------------------- COMMANDS -------------------
    # Each returns text to send (or None)

    async def cmd_about(self, user: str, arg: str) -> str | None:
        return (
            "HeyGuys 👋 I’m an AI-powered chatbot built with ChatGPT-5. "
            "I hang out in offline chat to keep things lively — "
            "ask me for a joke, trivia, a quick story, or even some wisdom about touching grass. "
            "Think of me as your sidekick when the stream is quiet! ✨"
        )

    async def cmd_inputs(self, user: str, arg: str) -> str | None:
        return (
            "📋 Available commands: $about, $inputs, $joke, $nickname, $story, $touchgrass, $trivia, $image. "
            "Type one and let’s have some fun! 🎲"
        )

    async def cmd_touchgrass(self, user: str, arg: str) -> str | None:
        return (
            "🌱 Touching grass is science-backed self-care: it calms stress, lifts your mood, "
            "and reminds you there’s a world beyond the screen. Go on, give it a try! 😎"
        )

    async def cmd_joke(self, user: str, arg: str) -> str | None:
        banlist = "\n".join(self._recent_jokes[-10:])  # last 10 jokes

        prompt = (
            "You are an expert comedian performing live for a Twitch chat audience. "
            "You always deliver jokes that are fresh, original, and surprising. "
            "Do not reuse common stock jokes like the scarecrow one. "
            "Keep it short (1–2 lines) and Twitch-friendly. "
            "Avoid repeating any of these recent jokes:\n" + banlist
        )

        joke = await self._ask_openai(prompt)
        if joke:
            self._recent_jokes.append(joke)

        return joke

    async def cmd_nickname(self, user: str, arg: str) -> str | None:
        banlist = "\n".join(self._recent_nicknames[-10:])  # last 10 nicknames

        prompt = (
            "You are a playful nickname generator for Twitch chat. "
            "Come up with a short, creative, and fun nickname for a viewer. "
            "Avoid anything mean-spirited, overly long, or generic like 'buddy' or 'pal'. "
            "Think quirky gamer tags, inside-joke style names, or positive vibes. "
            "Output just one nickname, nothing else."
            "Avoid repeating any of these recent nicknames:\n" + banlist
        )

        nickname = await self._ask_openai(prompt)
        if nickname:
            self._recent_nicknames.append(nickname)

        return f"🎭 Your new nickname: {nickname}"

    async def cmd_story(self, user: str, arg: str) -> str | None:
        banlist = "\n".join(self._recent_stories[-10:])  # last 10 stories

        prompt = (
            "You are a master of ultra-short storytelling. "
            "Write a wholesome, original micro-story under 150 characters. "
            "Make it feel like a complete moment, not just advice or a quote. "
            "Avoid clichés and common examples. "
            "Do not repeat any of these recent stories:\n" + banlist
        )

        story = await self._ask_openai(prompt)
        if story:
            self._recent_stories.append(story)
        return f"📖 {story}"

    async def cmd_trivia(self, user: str, arg: str) -> str | None:
        banlist = "\n".join(self._recent_trivia[-10:])  # last 10 pieces of trivia
        topic = random.choice(
            ["history", "internet", "culture", "pop culture", "movies", "Twitch"]
        )

        prompt = (
            "You are a fun trivia master on Twitch. "
            f"Give me ONE surprising {topic} trivia fact in 150 characters or less. "
            "Keep it engaging and Twitch-friendly (no long dates or boring lists). "
            "Make it sound like something chat would say 'Whoa!' to."
            "Do not repeat any of these recent pieces of trivia:\n" + banlist
        )

        trivia = await self._ask_openai(prompt)
        if trivia:
            self._recent_trivia.append(trivia)
        return f"🤓 {trivia}"

    async def cmd_image(self, user: str, arg: str) -> str | None:
        desc = arg.strip()
        if not desc:
            return "🖼️ Please provide a description! Example: `$image a cyberpunk ramen shop at night`"

        url_or_path, err = self._generate_image(desc, size="1024x1024")
        if err:
            return err

        # If OpenAI gave a URL, share it; otherwise mention where it was saved locally
        if url_or_path.startswith("http"):
            return f"🖼️ Here’s your creation: {url_or_path}"
        else:
            return f"🖼️ Image saved locally: {url_or_path}"

    # ------------------- OpenAI helpers -------------------
    async def _ask_openai(self, prompt: str) -> str:

        import openai

        openai.api_key = os.getenv("OPENAI_API_KEY", "")
        if not openai.api_key:
            return "OpenAI API key missing."

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-4o", "gpt-3.5-turbo" depending on what you want
                messages=[
                    {"role": "system", "content": prompt},
                ],
                temperature=1.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print("OpenAI error:", e)
            return "⚠️ Sorry, I couldn't come up with a reply right now."

    # --- helper: OpenAI image gen (v1+ SDK) ---
    def _generate_image(
        self, prompt: str, size: str = "1024x1024"
    ) -> tuple[str | None, str | None]:
        """
        Returns (url_or_path, error_message). If OpenAI returns a URL, we use it.
        Otherwise we save base64 to logs/images and return the local path.
        """
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None, "⚠️ OpenAI API key not set."

        try:
            client = OpenAI(api_key=api_key)
            resp = client.images.generate(
                # mode=gpt-image-1, # your org must be registered to use the latest models
                prompt=prompt,
                size=size,
            )
            data = resp.data[0]

            # Prefer hosted URL if present
            url = getattr(data, "url", None)
            if url:
                return url, None

            # Fallback: base64 -> save locally
            b64 = getattr(data, "b64_json", None)
            if b64:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                out_dir = self.log_dir / "images"
                out_dir.mkdir(parents=True, exist_ok=True)
                file_path = out_dir / f"image_{ts}.png"
                with open(file_path, "wb") as f:
                    f.write(b64decode(b64))
                return str(file_path), None

            return None, "⚠️ No image data returned."
        except Exception as e:
            print("OpenAI Image error:", e)
            return None, "⚠️ Sorry, I couldn’t generate that image right now."


# ----------------- quick runner -----------------
if __name__ == "__main__":
    load_dotenv("resources/appSettings.env")

    def split_list(val: str) -> list[str]:
        raw = (val or "").replace(";", ",")
        return [s.strip().lstrip("#").lower() for s in raw.split(",") if s.strip()]

    CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
    ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")  # user token
    BOT_USER_ID = os.getenv("TWITCH_BOT_ID")  # numeric id (your account)
    INITIAL_CHANNELS = split_list(os.getenv("INITIAL_CHANNELS"))
    LOG_DIR = os.getenv("LOG_DIRECTORY", "logs")
    PREFIXES = split_list(os.getenv("PREFIX"))

    for k, v in [
        ("TWITCH_CLIENT_ID", CLIENT_ID),
        ("TWITCH_ACCESS_TOKEN", ACCESS_TOKEN),
        ("TWITCH_BOT_ID", BOT_USER_ID),
    ]:
        if not v:
            raise SystemExit(f"Missing {k} in env")

    bot = EventSubChatBot(
        client_id=CLIENT_ID,
        access_token=ACCESS_TOKEN,
        bot_user_id=BOT_USER_ID,
        channel_logins=INITIAL_CHANNELS or ["riotgames"],  # default fallback
        log_directory=LOG_DIR or "C:/twitch_logs",
        active=True,
        prefixes=PREFIXES or ["$"],
    )

    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("Shutting down…")
        try:
            asyncio.run(bot.stop())
        except Exception:
            pass
