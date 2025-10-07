# bot/app.py
from __future__ import annotations

import asyncio
import contextlib
import inspect
import signal
from typing import Awaitable, Callable, Dict

from bot.bootstrap import (
    CLIENT_ID,
    ACCESS_TOKEN,
    BOT_USER_ID,
    INITIAL_CHANNELS,
    LOG_DIR,
    PREFIXES,
)
from bot.eventsub_bot import EventSubChatBot
from bot.handlers import handle_chat_message


def _make_command_bridge(bot: EventSubChatBot) -> Callable[[Dict], Awaitable[None]]:
    """Create a coroutine that adapts EventSub events to the command handler.

    The bridge extracts safe fields from the EventSub 'channel.chat.message' event
    and delegates to `handle_chat_message`. Any missing-key issues are logged and
    ignored (to avoid crashing the WS loop on malformed frames).

    Args:
        bot: The active EventSubChatBot instance.

    Returns:
        Coroutine function accepting a raw EventSub event dict.
    """

    async def _bridge(event: Dict) -> None:
        try:
            channel_login = event["broadcaster_user_login"]
            broadcaster_id = event["broadcaster_user_id"]
            user_login = event["chatter_user_login"]
            text = event["message"]["text"]
        except KeyError as e:
            # Be resilient to upstream schema changes or partial events
            print(f"[bridge] Missing key in event payload: {e!s}. Event: {event}")
            return

        await handle_chat_message(
            broadcaster_id=broadcaster_id,
            channel_login=channel_login,
            user_login=user_login,
            text=text,
            api_send=bot.send_message,
            suppress_when_live=getattr(bot, "_suppress_when_live", True),
            is_live_fn=bot.is_channel_live,
        )

    return _bridge


def build_bot() -> EventSubChatBot:
    """Construct and configure the EventSubChatBot from loaded env values."""
    bot = EventSubChatBot(
        client_id=CLIENT_ID,
        access_token=ACCESS_TOKEN,
        bot_user_id=BOT_USER_ID,
        channel_logins=list(INITIAL_CHANNELS or ["riotgames"]),
        log_directory=LOG_DIR or "logs",
        active=True,
        prefixes=PREFIXES or ("$",),
        suppress_when_live=True,
    )

    # Attach the command bridge the WS handler will call.
    bot._command_bridge = _make_command_bridge(bot)
    return bot


async def _run_with_signals(coro: Awaitable[None]) -> None:
    """Run a coroutine until completion, handling Ctrl+C/SIGTERM gracefully."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _request_stop(*_: object) -> None:
        stop_event.set()

    # Best-effort signal handling (SIGTERM not on Windows Git Bash sometimes)
    with contextlib.ExitStack() as stack:
        for sig in (signal.SIGINT, getattr(signal, "SIGTERM", None)):
            if sig is None:
                continue
            try:
                loop.add_signal_handler(sig, _request_stop)
                stack.callback(loop.remove_signal_handler, sig)
            except NotImplementedError:
                # Windows without Proactor or environments that don’t support signals
                pass

        task = asyncio.create_task(coro)

        # Wait for either the task to finish or a stop signal
        done, pending = await asyncio.wait(
            {task, asyncio.create_task(stop_event.wait())},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if stop_event.is_set():
            # If we received a stop signal, cancel the main task
            for t in pending:
                t.cancel()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def run() -> None:
    """Entry point used by main.py."""
    bot = build_bot()

    # Sanity check: ensure start is async
    assert inspect.iscoroutinefunction(
        bot.start
    ), "bot.start must be defined as `async def start(self):`"

    try:
        asyncio.run(_run_with_signals(bot.start()))
    except KeyboardInterrupt:
        # Redundant in most cases due to signal handling, but harmless.
        pass
    except asyncio.CancelledError:
        # Normal shutdown path when we cancel on signal.
        pass
    except Exception as e:
        # Print rich traceback and re-raise so CI tooling surfaces failures.
        import traceback

        print("[app] Unhandled exception during run():")
        traceback.print_exc()
        raise e
    finally:
        # Try to close the websocket cleanly
        try:
            asyncio.run(bot.stop())
        except Exception:
            pass
