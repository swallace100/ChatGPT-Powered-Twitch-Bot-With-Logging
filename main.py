# Get Twitch Access Token at https://twitchtokengenerator.com/
from twitchio.ext import commands
from datetime import datetime
import random
import os


# This is the class for the bot. Only one class can be active at once as far as I can tell.
class FrogBot(commands.Bot):

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot.
        # Add or remove prefixes that will activate bot actions. Multiple prefixes can be used.
        # initial_channels are the channels the bot will join. Add more channels as desired.
        super().__init__(token='ADD YOUR TOKEN HERE', prefix=['fro'], initial_channels=['riotgames'])

    async def event_ready(self):
        # Print message when bot is logged in and activated.
        print('Frogbot is up. Pog the Frogs!')

    async def event_message(self, message):
        # Messages with echo set to True are messages sent by the bot...
        if message.echo:
            return

        user = message.author.name
        channel_name = message.channel.name

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.date()

        # This prints all messages to the console.
        print(f'{current_date} {current_time} {user}: {message.content}')

        # Writes date and time of all messages to a text file.
        # Text files are in the logs folder and divided by channel name.
        # Writes date and time of when a user joined the channel to a text file.
        # Text files are in the logs folder and divided by channel name.
        parent_dir = "C:/Users/swall/PycharmProjects/twitchbot/logs/"
        child_dir = (f"{channel_name}/{current_date}")
        path = os.path.join(parent_dir, child_dir)
        if os.path.exists(path) == False:
            os.makedirs(path)
        else:
            pass

        file_object = open(f'./logs/{channel_name}/{current_date}/{current_date}.txt', 'a')
        file_object.write(f'{current_date} {current_time} {user}: {message.content}\n')
        file_object.close()

        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)

    # This function prints when someone joins the channel and records the time.
    async def event_join(self, channel, user):
        username = user.name
        channel_name = channel.name

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.date()
        print (f'{username}  joined channel {channel_name} on {current_date} at {current_time}')

        # Writes date and time of when a user joined the channel to a text file.
        # Text files are in the logs folder and divided by channel name.
        parent_dir = "SET THE DIRECTORY HERE"
        child_dir = (f"{channel_name}/{current_date}")
        path = os.path.join(parent_dir, child_dir)
        if os.path.exists(path) == False:
            os.makedirs(path)
        else:
            pass

        file_object = open(f'./logs/{channel_name}/{current_date}/{current_date}.txt', 'a')
        file_object.write(f'{current_date} {current_time} {username} joined channel {channel_name} \n')
        file_object.close()

    @commands.command()
    async def gs(self, ctx: commands.Context):
        # This command activates when someone types a word with a prefix listed about plus "gs"
        # This is supposed to activate when someone types the word "frogs"

        # Use random to set a range of responses for FrogBot
        number = random.randrange(3)

        # FrogBot pogs the frogs in chat! Response changes based on the random number generated.
        if number == 0:
            await ctx.send('PogChamp OSFrog OSFrog OSFrog')
        elif number == 1:
            await ctx.send('I like frogs OSFrog OSFrog OSFrog')
        else:
            await ctx.send("help me step- OSFrog i'm stuck")

    @commands.command()
    async def g(self, ctx: commands.Context):
        # This command is the same as above except it activates when someone types "frog"
        number = random.randrange(3)

        if number == 0:
            await ctx.send('PogChamp OSFrog')
        elif number == 1:
            await ctx.send('do you know jeremiah?')
        else:
            await ctx.send("fun fact. male frogs give female frogs boxes of flies on valentines day")


if __name__ == '__main__':
    keywordbot = FrogBot()
    keywordbot.run()
