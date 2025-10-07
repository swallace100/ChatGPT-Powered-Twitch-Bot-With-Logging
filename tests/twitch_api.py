import responses
from bot.twitch_api import TwitchApi, HELIX


@responses.activate
def test_resolve_logins():
    api = TwitchApi(client_id="cid", access_token="token")
    responses.add(
        responses.GET,
        f"{HELIX}/users?login=foo&login=bar",
        json={"data": [{"login": "foo", "id": "1"}, {"login": "bar", "id": "2"}]},
        status=200,
    )
    out = api.resolve_logins(["foo", "bar"])
    assert out == {"foo": "1", "bar": "2"}


@responses.activate
def test_is_live_caches():
    api = TwitchApi(client_id="cid", access_token="token")
    responses.add(
        responses.GET,
        f"{HELIX}/streams?user_id=1",
        json={"data": [{"id": "s"}]},
        status=200,
    )
    assert api.is_live("1") is True
    # second call should not trigger a second request (cache hit)
    assert api.is_live("1") is True
    assert len(responses.calls) == 1
