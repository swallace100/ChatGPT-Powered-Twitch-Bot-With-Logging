import pytest


class FakeAI:
    def __init__(self, text="ok", image_url="http://img"):
        self.text = text
        self.image_url = image_url

    def chat(self, prompt: str):
        return self.text

    def image(self, prompt: str, size: str):
        return self.image_url, None


@pytest.fixture
def fake_ai():
    return FakeAI()


@pytest.fixture
def env_setup(monkeypatch, tmp_path):
    # Keep tests isolated from your real env
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TWITCH_CLIENT_ID", "cid")
    monkeypatch.setenv("TWITCH_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TWITCH_BOT_ID", "123")
    monkeypatch.setenv("LOG_DIRECTORY", str(tmp_path / "logs"))
    yield
