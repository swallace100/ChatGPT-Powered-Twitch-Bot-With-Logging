from bot.commands import CommandRegistry
from bot.commands import register_builtins
import pytest


@pytest.mark.asyncio
async def test_builtins_joke_uses_ai(fake_ai):
    reg = CommandRegistry(prefixes=("$",))
    register_builtins(reg, fake_ai)

    from bot.commands import CommandContext

    ctx = CommandContext(broadcaster_id="b", channel_login="c", user_login="u")
    # Run twice; second time should still return text and record history
    r1 = await reg.dispatch(ctx, "$joke")
    r2 = await reg.dispatch(ctx, "$joke")
    assert r1 and r1.strip()
    assert r2 and r2.strip()


@pytest.mark.asyncio
async def test_image_happy_path(fake_ai):
    reg = CommandRegistry(prefixes=("$",))
    register_builtins(reg, fake_ai)
    from bot.commands import CommandContext

    ctx = CommandContext(broadcaster_id="b", channel_login="c", user_login="u")
    out = await reg.dispatch(ctx, "$image a cat in space")
    assert "http://" in out or "https://" in out
