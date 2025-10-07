# 🎥 ChatGPT-Powered Twitch Bot with Logging

![Python](https://img.shields.io/badge/Python-3.13+-blue)
![Twitch API](https://img.shields.io/badge/Twitch-EventSub-purple)
![OpenAI](https://img.shields.io/badge/OpenAI-API-orange)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Build](https://img.shields.io/badge/Status-Ready--to--Run-success)

> An **AI-powered Twitch chatbot** built with Python 3.13+, EventSub WebSockets, and OpenAI.

This bot keeps **offline Twitch chats alive** — telling jokes, sharing trivia, generating nicknames, and creating AI-generated images — while **logging every message** in neatly organized per-channel folders for later review or analytics.

---

## ✨ Features

- **Modern EventSub listener** (no deprecated IRC)
- **OpenAI integration** for text + image generation
- **Built-in fun commands**:
  | Command | Description |
  |----------|-------------|
  | `$about` | Introductory message |
  | `$inputs` | List available commands |
  | `$joke` | Generates a fresh, original Twitch-friendly joke |
  | `$nickname` | Suggests a quirky nickname |
  | `$story` | Tiny wholesome micro-stories |
  | `$touchgrass` | Gentle self-care reminders |
  | `$trivia` | Surprising trivia facts |
  | `$image <desc>` | AI-generated images |
- **Structured chat logging** to `logs/<channel>/<date>/`
- **Command cooldowns** to avoid spam
- **Clean modular architecture** (OpenAI service, Twitch API helper, command registry)

---

## 🏗️ Architecture

```bash
bot/
  __init__.py
  config.py            # Loads .env, parses types, sets defaults
  twitch_api.py        # Helix REST calls (send_message, users, streams)
  eventsub_bot.py      # WebSocket session + subscriptions
  commands/
    __init__.py
    registry.py        # CommandRegistry + CommandContext
    builtins.py        # about, inputs, joke, nickname, story, trivia, image
  services/
    openai_service.py  # Text + image generation via OpenAI
    logger.py          # File logging (path management & writes)
  handlers.py          # Message dispatch bridge
  app.py               # Wire everything together and run
resources/
  appSettings.env_example
tests/
  test_*.py
```

## Requirements

- Python 3.13+
- Dependencies:

```bash
make install
```

or for development

```bash
make install-dev
```

- Acounts
  - Twitch Dev account: [Twitch Dev Console](https://dev.twitch.tv/console/apps)
  - OpenAPI API Key: [OpenAI API Dashboard](https://platform.openai.com/api-keys)

## 🔑 Configuration

Copy and edit the example environment file:

```bash
cp resources/appSettings.env_example resources/appSettings.env
```

Populate it with your Twitch and OpenAI credentials:

```env
OPENAI_API_KEY=sk-...
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_secret
TWITCH_ACCESS_TOKEN=
TWITCH_REFRESH_TOKEN=
TWITCH_BOT_ID=your_numeric_id
INITIAL_CHANNELS=riotgames
PREFIX=$
LOG_DIRECTORY=logs
```

Then run the helper to obtain a valid Twitch access token:

```bash
python get_tokens.py
```

The script will guide you through Twitch’s Device Code flow, open your browser, and update `resources/appSettings.env` automatically.

## 🚀 Usage

- On startup, the bot connects to Twitch’s EventSub WebSocket (`wss://eventsub.wss.twitch.tv/ws`).
- Subscribes to `channel.chat.message` events for each channel in `INITIAL_CHANNELS`.
- On receiving a chat message:
  - Logs it to disk
  - Checks for command prefixes
  - Dispatches to the matching command handler
- Sends responses back via POST /helix/chat/messages (requires user:write:chat scope).

## Usage

```bash
make install-dev
make run
```

Or manually:

```bash
python main.py
```

Once running, the bot will:

1. Connect to the EventSub WebSocket (`wss://eventsub.wss.twitch.tv/ws`).

2. Subscribe to `channel.chat.message` events for each channel listed in `INITIAL_CHANNELS`.

3. Log all messages and respond when commands are invoked.

Example:

```text
[streamer678] user123: $joke
Bot: Why did the GPU go to therapy? It couldn't handle the parallel stress.
```

## 🧪 Testing

Lightweight test suite using `pytest` and `pytest-asyncio`.

```bash
make test
```

To run with coverage:

```bash
pytest --cov=bot
```

## 🧰 Tech Stack

- Python 3.13+
- Twitch EventSub API → [docs](https://dev.twitch.tv/docs/eventsub)
- OpenAI API for chat + image generation
- dotenv for environment management
- Ruff + Black + pre-commit for linting/formatting
- pytest for testing

## 🧩 Development Workflow

```bash
make install-dev   # Install dev dependencies
make precommit     # Run lint + format hooks
make test          # Run unit tests
```

Hooks are configured in `pyproject.toml` and automatically installed via `pre-commit`.

## 🗂️ Logging Output

Each message is saved under:

```txt
logs/<channel>/<YYYY-MM-DD>/<YYYY-MM-DD>.txt
```

Example entry:

```txt
2025-10-07 21:15:34 user123: $story
```

## 🪪 License

This project is distributed under the MIT License — see [LICENSE](./LICENSE) for details.

## 🤝 Contributing

Pull requests are welcome!
Please lint and test before submitting:

```bash
make precommit && make test
```

## 🧠 Author

Steven Wallace
GitHub: https://www.github.com/swallace100
