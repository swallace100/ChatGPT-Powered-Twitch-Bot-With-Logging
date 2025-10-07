from __future__ import annotations

import random
from collections import deque
from typing import Optional, Deque, Iterable

from .registry import CommandRegistry, CommandContext, CommandHandler

# Expected service interface:
#   - openai_service.chat(prompt: str) -> Optional[str]
#   - openai_service.image(prompt: str, size: str) -> tuple[Optional[str], Optional[str]]


class BuiltinCommands:
    """Holds ephemeral state (recent outputs) and implements built-in command handlers.

    Args:
        openai_service: Object that provides `chat()` and `image()` methods.
        max_history: Max number of recent outputs to keep for de-duplication.
    """

    def __init__(self, openai_service, max_history: int = 10):
        self.ai = openai_service
        self.recent_jokes: Deque[str] = deque(maxlen=max_history)
        self.recent_stories: Deque[str] = deque(maxlen=max_history)
        self.recent_trivia: Deque[str] = deque(maxlen=max_history)
        self.recent_nicknames: Deque[str] = deque(maxlen=max_history)

    # ----- helpers -----

    @staticmethod
    def _join_recent(items: Iterable[str]) -> str:
        """Return a newline-joined string of recent items (or empty string)."""
        return "\n".join(items) if items else ""

    # ----- handlers (all async, return Optional[str]) -----

    async def about(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Describe the bot and its purpose."""
        return (
            "HeyGuys 👋 I’m an AI-powered chatbot built with ChatGPT-5. "
            " I hang out in offline chat to keep things lively — "
            "ask me for $joke, $trivia, $story, $nickname, or $image. ✨"
        )

    async def inputs(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """List available commands."""
        return "📋 Commands: $about, $inputs, $joke, $nickname, $story, $touchgrass, $trivia, $image"

    async def touchgrass(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Encourage a brief wellness break."""
        return (
            "🌱 Touch grass break: breathe, stretch, and look at something far away. "
            "Your brain will thank you. 😎"
        )

    async def joke(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Generate one short, original, Twitch-friendly joke."""
        banlist = self._join_recent(self.recent_jokes)
        prompt = (
            "You are a stand-up comic performing for Twitch chat. "
            "Deliver one fresh, original, Twitch-friendly joke (1–2 lines). "
            "Avoid stock jokes and anything mean-spirited. "
            "Do not repeat any of these recent jokes:\n" + banlist
        )
        joke = self.ai.chat(prompt)
        if joke:
            self.recent_jokes.append(joke)
        return joke

    async def nickname(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Generate a playful nickname; return a formatted response."""
        banlist = self._join_recent(self.recent_nicknames)
        prompt = (
            "You are a playful nickname generator for Twitch chat. "
            "Output ONE short, creative, positive nickname only—no extra text. "
            "Avoid generic terms (buddy, pal) and anything rude. "
            "Do not repeat any of these recent nicknames:\n" + banlist
        )
        name = self.ai.chat(prompt)
        if name:
            self.recent_nicknames.append(name)
            return f"🎭 Your new nickname: {name}"
        return None

    async def story(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Generate a wholesome micro-story under 150 characters."""
        banlist = self._join_recent(self.recent_stories)
        prompt = (
            "Write an original micro-story under 150 characters. "
            "Make it a complete moment (not advice or a quote). "
            "Avoid clichés. "
            "Do not repeat any of these recent stories:\n" + banlist
        )
        story = self.ai.chat(prompt)
        if story:
            self.recent_stories.append(story)
            return f"📖 {story}"
        return None

    async def trivia(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Return a punchy, surprising trivia fact (≤150 chars)."""
        banlist = self._join_recent(self.recent_trivia)
        topic = arg.strip() or random.choice(
            [
                "history",
                "internet",
                "culture",
                "movies",
                "Twitch",
                "science",
                "nature",
                "space",
                "technology",
                "music",
                "games",
            ]
        )
        prompt = (
            f"Give ONE surprising {topic} trivia fact in ≤150 characters. "
            "Keep it Twitch-friendly and punchy. "
            "Make chat say 'Whoa!'. "
            "Do not repeat any of these:\n" + banlist
        )
        fact = self.ai.chat(prompt)
        if fact:
            self.recent_trivia.append(fact)
            return f"🤓 {fact}"
        return None

    async def image(self, ctx: CommandContext, arg: str) -> Optional[str]:
        """Create an image via the OpenAI image API and return a shareable message."""
        desc = arg.strip()
        if not desc:
            return "🖼️ Please provide a description! Example: `$image a cyberpunk ramen shop at night`"
        url_or_path, err = self.ai.image(desc, size="1024x1024")
        if err:
            return f"⚠️ {err}"
        if url_or_path and url_or_path.startswith("http"):
            return f"🖼️ Here’s your creation: {url_or_path}"
        if url_or_path:
            return f"🖼️ Image saved locally: {url_or_path}"
        return "⚠️ No image returned."


def register_builtins(registry: CommandRegistry, openai_service) -> BuiltinCommands:
    """Register all built-in command handlers on a registry.

    Args:
        registry: CommandRegistry instance to populate.
        openai_service: Service that implements `chat()` and `image()`.

    Returns:
        BuiltinCommands: The stateful command provider instance.
    """
    cmds = BuiltinCommands(openai_service)

    # map names to handlers
    mapping: dict[str, CommandHandler] = {
        "about": cmds.about,
        "inputs": cmds.inputs,
        "joke": cmds.joke,
        "nickname": cmds.nickname,
        "story": cmds.story,
        "touchgrass": cmds.touchgrass,
        "trivia": cmds.trivia,
        "image": cmds.image,
    }
    for name, fn in mapping.items():
        registry.register(name, fn)

    # optional aliases
    registry.add_alias("help", "inputs")
    registry.add_alias("commands", "inputs")

    return cmds
