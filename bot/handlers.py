from __future__ import annotations

from typing import Awaitable, Callable, Optional

from bot.commands import CommandContext
from bot.bootstrap import registry, BOT_USER_ID

# api_send: (broadcaster_id, sender_id, message) -> None
# is_live_fn: async (broadcaster_id) -> bool


async def handle_chat_message(
    broadcaster_id: str,
    channel_login: str,
    user_login: str,
    text: str,
    api_send: Callable[[str, str, str], None],
    suppress_when_live: bool,
    is_live_fn: Callable[[str], Awaitable[bool]],
) -> None:
    """Parse a chat line and dispatch a command, sending a reply if produced.

    Args:
        broadcaster_id: Numeric Twitch user ID for the channel.
        channel_login: Channel login name (displayed in logs).
        user_login: The chatter’s login name.
        text: Full chat message.
        api_send: Callable used to send chat messages (bot.send_message).
        suppress_when_live: If True, do not run commands while the channel is live.
        is_live_fn: Async function to check live state for the broadcaster.

    Notes:
        - This function is intentionally small: parsing/dispatch lives in `registry`.
        - Exceptions from command handlers are caught and logged so the WS loop
          continues running even if one command misbehaves.
    """
    if not text:
        return

    # Optional guard: don't respond during live streams
    if suppress_when_live and await is_live_fn(broadcaster_id):
        print(f"#{channel_login} is live — command suppressed.")
        return

    ctx = CommandContext(
        broadcaster_id=broadcaster_id,
        channel_login=channel_login,
        user_login=user_login,
    )

    try:
        reply: Optional[str] = await registry.dispatch(ctx, text)
    except Exception as e:
        # Never let a bad handler take down the socket loop
        print(f"[handlers] Command dispatch error: {e!r}")
        return

    if reply:
        try:
            api_send(broadcaster_id, BOT_USER_ID, reply)
        except Exception as e:
            print(f"[handlers] Failed to send message: {e!r}")
