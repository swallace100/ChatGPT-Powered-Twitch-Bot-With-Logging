from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

__all__ = ["BotConfig", "load_config"]


def _split_list(val: str | None) -> list[str]:
    """Split a comma/semicolon-separated string into a cleaned list of lowercased tokens."""
    raw = (val or "").replace(";", ",")
    return [s.strip().lstrip("#").lower() for s in raw.split(",") if s.strip()]


@dataclass(frozen=True)
class BotConfig:
    """Immutable configuration container for the Twitch EventSub chatbot."""

    # --- Twitch credentials ---
    client_id: str
    access_token: str  # user access token
    bot_user_id: str  # numeric id of the bot account
    initial_channels: Tuple[str, ...]  # channels to join

    # --- Bot behavior ---
    log_directory: str  # log storage base path
    prefixes: Tuple[str, ...]  # command prefixes (e.g. "$", "!")

    # --- Misc metadata ---
    env_file: Path  # path to the loaded .env file


def load_config(env_file: str | os.PathLike = "resources/appSettings.env") -> BotConfig:
    """
    Load environment variables from an appSettings.env file (or shell environment)
    and return a validated BotConfig instance.

    Args:
        env_file: Path to the .env file containing bot configuration values.

    Returns:
        BotConfig instance populated from environment variables.

    Raises:
        SystemExit: if required Twitch credentials are missing.
    """
    env_path = Path(env_file)
    if not env_path.exists():
        print(
            f"[config] WARNING: env file not found at {env_path.resolve()}. Using shell environment only."
        )
    load_dotenv(env_path)

    # --- Parse Twitch credentials ---
    client_id = os.getenv("TWITCH_CLIENT_ID", "")
    access_token = os.getenv("TWITCH_ACCESS_TOKEN", "")
    bot_user_id = os.getenv("TWITCH_BOT_ID", "")

    # --- Parse behavior settings ---
    initial_channels: List[str] = _split_list(os.getenv("INITIAL_CHANNELS"))
    log_dir = os.getenv("LOG_DIRECTORY", "logs")
    prefixes: List[str] = _split_list(os.getenv("PREFIX")) or ["$"]

    # --- Validation ---
    missing = [
        k
        for k, v in [
            ("TWITCH_CLIENT_ID", client_id),
            ("TWITCH_ACCESS_TOKEN", access_token),
            ("TWITCH_BOT_ID", bot_user_id),
        ]
        if not v
    ]
    if missing:
        raise SystemExit(
            f"Missing required env keys: {', '.join(missing)}\n"
            f"(Check your {env_path.name} or environment configuration.)"
        )

    # --- Construct configuration object ---
    return BotConfig(
        client_id=client_id,
        access_token=access_token,
        bot_user_id=bot_user_id,
        initial_channels=tuple(initial_channels or ["riotgames"]),
        log_directory=log_dir,
        prefixes=tuple(prefixes or ["$"]),
        env_file=env_path,
    )
