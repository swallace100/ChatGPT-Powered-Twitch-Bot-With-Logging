import pytest
from bot.handlers import handle_chat_message


@pytest.mark.asyncio
async def test_handle_chat_message_suppresses_when_live(monkeypatch):
    sent = {}

    async def is_live(_):
        return True

    def api_send(bid, sid, msg):
        sent["msg"] = msg

    await handle_chat_message(
        broadcaster_id="b1",
        channel_login="chan",
        user_login="user",
        text="$about",
        api_send=api_send,
        suppress_when_live=True,
        is_live_fn=is_live,
    )
    assert "msg" not in sent  # suppressed


@pytest.mark.asyncio
async def test_handle_chat_message_dispatches(monkeypatch):
    # Force registry to respond predictably
    from bot import bootstrap

    async def fake_dispatch(ctx, text):
        return "ok!"

    monkeypatch.setattr(bootstrap.registry, "dispatch", fake_dispatch)

    collected = {}

    async def not_live(_):
        return False

    def api_send(bid, sid, msg):
        collected["msg"] = msg

    await handle_chat_message(
        broadcaster_id="b1",
        channel_login="chan",
        user_login="user",
        text="$anything",
        api_send=api_send,
        suppress_when_live=True,
        is_live_fn=not_live,
    )
    assert collected["msg"] == "ok!"
