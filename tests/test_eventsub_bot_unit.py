import pytest
import responses
from bot.eventsub_bot import EventSubChatBot, HELIX


@pytest.mark.asyncio
async def test_is_channel_live(monkeypatch):
    bot = EventSubChatBot(
        client_id="cid",
        access_token="token",
        bot_user_id="42",
        channel_logins=["foo"],
        log_directory="logs",
    )
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET, f"{HELIX}/streams", json={"data": [{"id": "s"}]}, status=200
        )
        live = await bot.is_channel_live("123")
        assert live is True


@responses.activate
def test_resolve_logins_to_ids(monkeypatch):
    bot = EventSubChatBot(
        client_id="cid",
        access_token="token",
        bot_user_id="42",
        channel_logins=["foo", "bar"],
        log_directory="logs",
    )
    responses.add(
        responses.GET,
        f"{HELIX}/users",
        json={"data": [{"login": "foo", "id": "1"}, {"login": "bar", "id": "2"}]},
        status=200,
    )
    bot._resolve_logins_to_ids()
    assert bot._login_to_id == {"foo": "1", "bar": "2"}
