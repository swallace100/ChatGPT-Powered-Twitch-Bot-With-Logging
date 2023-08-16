# ChatGPT and Dall-E Powered Twitch Bot with Logging

## Description
  
- There weren't many tutorials on how to make Twitch bots using the site's APIs, so I made one using the API documentation.
- This bot connects with ChatGPT 3.5-Turbo to create jokes, stories, nicknames, and trivia.
- Dall-E is used to create images based on a prompt. Dall-E is much more expensive to use compared to ChatGPT 3.5, so keep that in mind when using.
- ChatGPT created the responses for TouchGrass and About, but I just reuse the response I got from it earlier.
- The list of commands is $About, $Draw, $Commands, $Joke, $Nickname, $Story, $TouchGrass, and $Trivia.
- It is set to only work with the streamer is offline so that it doesn't interfere with the stream's online chat.
- All chat messages are saved to a designated folder.
  
- There are a lot of powerful moderator bots out there, but this one is for offline chat interaction with ChatGPT/Dall-E and chat logging. 

## Installation

- This can be run on any development platform with Python support, such as PyCharm or Visual Studio Code.
- Users may need to install twitchio.ext and openai

## Usage

- Individual secret keys provided by Twitch are required to access the API. Please follow the steps here to acquire yours https://dev.twitch.tv/docs/authentication/
- Individual secret keys provided by OpenAI are also required. Create an account with OpenAI and go here to get the key https://platform.openai.com/account/api-keys
  
- A file path must also be provided in the designated line in the code for the chat logs to be saved.
  
- There are pre-set keywords that the bot will respond to, but those can be changed.

## Built With

- Python
- Twitch's API - https://dev.twitch.tv/docs/api/
- TwitchIO Library - https://twitchio.dev/en/latest/
- OpenAI API - https://platform.openai.com/docs/api-reference

## License

Distributed under the MIT License.


