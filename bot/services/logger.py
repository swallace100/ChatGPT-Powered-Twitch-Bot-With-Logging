from __future__ import annotations

import datetime as _dt
from pathlib import Path


class LogWriter:
    """File-based logger for per-channel chat and image logs.

    Structure:
        logs/<channel>/<YYYY-MM-DD>/<YYYY-MM-DD>.txt

    Each appended line:
        "YYYY-MM-DD HH:MM:SS user: message"

    Attributes:
        base: Root log directory (default: "logs").
    """

    def __init__(self, base_dir: str | Path = "logs") -> None:
        """Initialize a logger rooted at the given directory."""
        self.base: Path = Path(base_dir)

    def log_message(self, channel: str, user: str, text: str) -> Path:
        """Append one chat message line to the appropriate log file.

        Args:
            channel: Twitch channel login name.
            user: Name of the chatter.
            text: Raw message content.

        Returns:
            Path to the log file that was written.
        """
        now = _dt.datetime.now()
        date_str = now.date().isoformat()
        time_str = now.strftime("%H:%M:%S")

        path = self.base / channel / date_str
        path.mkdir(parents=True, exist_ok=True)

        file_path = path / f"{date_str}.txt"
        with file_path.open("a", encoding="utf-8") as f:
            f.write(f"{date_str} {time_str} {user}: {text}\n")

        return file_path

    def ensure_images_dir(self) -> Path:
        """Ensure that the images subdirectory (logs/images) exists.

        Returns:
            Path to the created or existing images directory.
        """
        out = self.base / "images"
        out.mkdir(parents=True, exist_ok=True)
        return out
