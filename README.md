# ChatGPT Powered Twitch Bot with Logging

## Description

- An AI-powered Twitch chatbot built with EventSub WebSockets and OpenAI.
- It hangs out in offline chat to entertain viewers when streams are quiet — delivering jokes, trivia, micro-stories, nicknames, and even AI-generated images.
- All messages are logged per channel/day for history.

## Architecture

```graphql
bot/
  __init__.py
  config.py            # load .env, parse types, defaults
  twitch_api.py        # Helix REST calls (send_message, users, streams)
  eventsub_ws.py       # WebSocket session + subscriptions
  commands/
    __init__.py
    registry.py        # CommandRegistry + CommandContext
    builtins.py        # about, inputs, joke, nickname, story, trivia, image
  services/
    openai_service.py  # text + image methods; one client instance
    logger.py          # file logging (path mgmt and write)
  app.py               # wire everything and run
```

## Features

- EventSub-based chat listener (no deprecated IRC)
- Configurable prefixes (default: $)
- Built-in commands:
  - $about – bot introduction
  - $inputs – list of commands
  - $joke – fresh, original jokes (avoids repeats)
  - $nickname – quirky, fun nickname ideas
  - $story – ultra-short wholesome micro-stories
  - $touchgrass – self-care reminders
  - $trivia – surprising trivia facts
  - $image <desc> – AI-generated images
- Logging of all chat to logs/<channel>/<date>/...
- Auto cooldown (activation_timer) so it doesn’t spam

## Requirements

- Python 3.13+
- Dependencies: pip install openai python-dotenv requests websockets
- Twitch application credentials from Twitch Dev Console
- An OpenAI API key from OpenAI

## How It Works

- On startup, the bot connects to Twitch’s EventSub WebSocket (wss://eventsub.wss.twitch.tv/ws).
- Subscribes to channel.chat.message events for each channel in INITIAL_CHANNELS.
- On receiving a chat message:
  - Logs it to disk
  - Checks for command prefixes
  - Dispatches to the matching command handler
- Sends responses back via POST /helix/chat/messages (requires user:write:chat scope).

## Usage

- Individual secret keys provided by Twitch are required to access the API. Please follow the steps here to acquire yours https://dev.twitch.tv/docs/authentication/
- Individual secret keys provided by OpenAI are also required. Create an account with OpenAI and go here to get the key https://platform.openai.com/account/api-keys
- There are pre-set keywords that the bot will respond to, but those can be changed.

Do not store your API or user keys in a GitHub repository.

`/resources/appSettings.env_example` shows how to set and safely store all the required variables for the app.

Set the TWITCH_CLIENT_ID value in the `appSettings.env` file then run `get_tokens.py` to populate the other authorization related variables. The Twitch client ID can be obtained by visiting https://dev.twitch.tv/console/apps.

The app must be registered with Twitch to obtain the Client ID. The Client Secret must also be created manually by visiting https://dev.twitch.tv/console/apps.

Run `python chatgpt_twitch_bot.py` in a CLI to start the application.

## Tech Stack

- Python
- Twitch EventSub API - https://dev.twitch.tv/docs/api/
- OpenAI (chat + image generation)
- dotenv for config
- Async WebSockets

## License

Distributed under the MIT License.
