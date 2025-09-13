# ChatGPT Powered Twitch Bot with Logging

## Description

- There weren't many tutorials on how to make Twitch bots using the site's APIs, so I made one using the API documentation.
- This bot connects with ChatGPT 4o to create jokes, stories, nicknames, and trivia.
- There is an option to allow users to create images, but it is much more expensive than text input, so keep that in mind when using.
- ChatGPT created the responses for TouchGrass and About, but I just reuse its earlier output.
- The list of commands is $About, $Draw, $Commands, $Joke, $Nickname, $Story, $TouchGrass, and $Trivia.
- It is set to only work with the streamer is offline so that it doesn't interfere with the stream's online chat.
- All chat messages are saved to a designated folder.
- There are a lot of powerful moderator bots out there, but this one is for offline chat interaction with ChatGPT and chat logging.

## Installation

- This can be run on any development platform with Python support, such as PyCharm or Visual Studio Code.
- Users may need to install twitchio.ext and openai

## Usage

- Individual secret keys provided by Twitch are required to access the API. Please follow the steps here to acquire yours https://dev.twitch.tv/docs/authentication/
- Individual secret keys provided by OpenAI are also required. Create an account with OpenAI and go here to get the key https://platform.openai.com/account/api-keys
- There are pre-set keywords that the bot will respond to, but those can be changed.

Do not store your API or user keys in a GitHub repository.

`/resources/appSettings.env_example` shows how to set and safely store all the required variables for the app.

Set the TWITCH_CLIENT_ID value in the `appSettings.env` file then run `get_tokens.py` to populate the other authorization related variables. The Twitch client ID can be obtained by visiting https://dev.twitch.tv/console/apps.

The app must be registered with Twitch to obtain the Client ID. The Client Secret must also be created manually by visiting https://dev.twitch.tv/console/apps.

## Tech Stack

- Python
- Twitch's API - https://dev.twitch.tv/docs/api/
- TwitchIO Library - https://twitchio.dev/en/latest/
- OpenAI API - https://platform.openai.com/docs/api-reference

## License

Distributed under the MIT License.
