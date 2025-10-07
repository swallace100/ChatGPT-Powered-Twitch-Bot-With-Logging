from bot.commands import CommandRegistry, CommandContext
import pytest


@pytest.mark.asyncio
async def test_registry_parse_and_dispatch():
    reg = CommandRegistry(prefixes=("$",))
    calls = {}

    async def echo(ctx: CommandContext, arg: str):
        calls["ctx"] = ctx
        return f"echo:{arg}"

    reg.register("echo", echo)

    # parse
    cmd, arg = reg.parse("$echo hi there")
    assert cmd == "echo"
    assert arg == "hi there"

    # dispatch
    ctx = CommandContext(broadcaster_id="b1", channel_login="chan", user_login="user")
    out = await reg.dispatch(ctx, "$echo hello")
    assert out == "echo:hello"
    assert calls["ctx"].channel_login == "chan"


def test_registry_alias():
    reg = CommandRegistry(prefixes=("!",))

    async def noop(ctx, arg):
        return None

    reg.register("one", noop)
    reg.add_alias("1", "one")
    assert "1" in reg.list_commands()
