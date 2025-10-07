from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

from bot.commands import CommandRegistry, register_builtins
from bot.services.openai_service import OpenAIService

# Public exports for other modules
__all__ = [
    "ENV_PATH",
    "OPENAI_API_KEY",
    "CLIENT_ID",
    "ACCESS_TOKEN",
    "BOT_USER_ID",
    "INITIAL_CHANNELS",
    "LOG_DIR",
    "PREFIXES",
    "registry",
    "openai_service",
]


# -------- configuration loading --------

ENV_PATH: str = "resources/appSettings.env"


def _split_list(val: str | None) -> list[str]:
    """Split a comma/semicolon separated env value into a clean list of strings."""
    raw = (val or "").replace(";", ",")
    return [s.strip().lstrip("#").lower() for s in raw.split(",") if s.strip()]


def _require(keys: list[tuple[str, str]]) -> None:
    """Raise SystemExit if any required env variable is missing."""
    missing = [k for k, v in keys if not v]
    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + f"\n(Load from {ENV_PATH} or your shell env)"
        )


def _load_env(env_path: str | os.PathLike = ENV_PATH) -> None:
    """Load environment variables from the given .env path if it exists."""
    p = Path(env_path)
    if not p.exists():
        # Not fatal—`load_dotenv` is a no-op if the file doesn't exist.
        # We still allow variables to come from the shell environment.
        print(
            f"bootstrap: WARNING: env file not found at {p.resolve()}; using shell env only."
        )
    load_dotenv(p)


# Actually load configuration from env/files
_load_env(ENV_PATH)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
CLIENT_ID: str = os.getenv("TWITCH_CLIENT_ID", "") or ""
ACCESS_TOKEN: str = os.getenv("TWITCH_ACCESS_TOKEN", "") or ""
BOT_USER_ID: str = os.getenv("TWITCH_BOT_ID", "") or ""  # numeric string
INITIAL_CHANNELS: Tuple[str, ...] = tuple(_split_list(os.getenv("INITIAL_CHANNELS")))
LOG_DIR: str = os.getenv("LOG_DIRECTORY", "logs")
PREFIXES: Tuple[str, ...] = tuple(_split_list(os.getenv("PREFIX")) or ["$"])

# Validate required values early
_require(
    [
        ("TWITCH_CLIENT_ID", CLIENT_ID),
        ("TWITCH_ACCESS_TOKEN", ACCESS_TOKEN),
        ("TWITCH_BOT_ID", BOT_USER_ID),
    ]
)

# -------- shared, process-wide services --------

# Command registry + OpenAI service (initialized once per process)
registry: CommandRegistry = CommandRegistry(prefixes=PREFIXES)
openai_service: OpenAIService = OpenAIService(api_key=OPENAI_API_KEY, log_dir=LOG_DIR)
register_builtins(registry, openai_service)
