from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Awaitable, Optional, Dict, Tuple


@dataclass(frozen=True)
class CommandContext:
    """Runtime context for a single command invocation.

    Attributes:
        broadcaster_id: Twitch broadcaster's numeric user ID.
        channel_login: Channel login name where the message appeared.
        user_login: Login name of the chatter invoking the command.
    """

    broadcaster_id: str
    channel_login: str
    user_login: str


# Async handler signature: (ctx, arg) -> Optional[str]
CommandHandler = Callable[[CommandContext, str], Awaitable[Optional[str]]]


class CommandRegistry:
    """Registry that parses prefixed chat messages and dispatches them to async handlers."""

    def __init__(self, prefixes: Tuple[str, ...] = ("$",)):
        """
        Initialize a new command registry.

        Args:
            prefixes: Tuple of recognized command prefixes (e.g., ("$", "!")).
        """
        if not isinstance(prefixes, tuple):
            prefixes = tuple(prefixes)
        self._prefixes: Tuple[str, ...] = prefixes
        self._handlers: Dict[str, CommandHandler] = {}

    # --- Registration ---

    def register(self, name: str, handler: CommandHandler) -> None:
        """
        Register a new command handler.

        Args:
            name: Command name (case-insensitive).
            handler: Async function implementing the command.
        """
        key = name.strip().lower()
        if not key:
            raise ValueError("Command name cannot be empty.")
        self._handlers[key] = handler

    def add_alias(self, alias: str, target: str) -> None:
        """
        Register an alias that points to an existing command.

        Args:
            alias: Alternate name for the command.
            target: Original registered command name to alias.
        Raises:
            KeyError: If the target command does not exist.
        """
        target_key = target.strip().lower()
        alias_key = alias.strip().lower()
        if target_key not in self._handlers:
            raise KeyError(f"Target command not found: {target}")
        self._handlers[alias_key] = self._handlers[target_key]

    # --- parsing ---

    def parse(self, text: str) -> Tuple[Optional[str], str]:
        """
        Parse a message for a prefixed command.

        Returns:
            tuple: (command, arg) or (None, "") if no valid prefix/command found.
        """
        if not text:
            return None, ""
        if not any(text.startswith(p) for p in self._prefixes):
            return None, ""
        prefix = next(p for p in self._prefixes if text.startswith(p))
        rest = text[len(prefix) :].strip()
        if not rest:
            return None, ""
        parts = rest.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        return cmd, arg

    # --- Dispatch ---

    async def dispatch(self, ctx: CommandContext, text: str) -> Optional[str]:
        """
        Execute the appropriate command handler for a message.

        Args:
            ctx (CommandContext): Context object containing channel/user info.
            text (str): Full chat message text.

        Returns:
            str | None: Command response string, or None if no match.
        """
        cmd, arg = self.parse(text)
        if not cmd:
            return None
        handler = self._handlers.get(cmd)
        if not handler:
            return None
        return await handler(ctx, arg)

    # --- Introspection ---

    def list_commands(self) -> Tuple[str, ...]:
        """
        Return a sorted tuple of all registered command names.
        """
        return tuple(sorted(self._handlers.keys()))

    @property
    def prefixes(self) -> Tuple[str, ...]:
        """
        Return the tuple of active command prefixes (e.g. "$", "!").
        """
        return self._prefixes
