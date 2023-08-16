# Get Twitch Access Token at https://twitchtokengenerator.com/
from twitchio.ext import commands
from datetime import datetime
import requests
import random
import os
import openai
import threading

openai.api_key = 'ADD YOUR SECRET KEY HERE'

# This is the class for the bot. Only one class can be active at once as far as I can tell.
# It is only meant to be used while the channel is offline.
class IntermissionBot(commands.Bot):

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot.
        # Add or remove prefixes that will activate bot actions. Multiple prefixes can be used.
        # initial_channels are the channels the bot will join. Add more channels as desired.
        super().__init__(token='ADD YOUR TOKEN HERE', prefix=['$'], initial_channels=['riotgames'])

        self._active = True

    def activation_timer(self):
        timer = threading.Timer(10, self.set_activation, args=[True])
        timer.start()

    def get_activation(self):
        return self._active

    def set_activation(self, status):
        self._active = status

        if status is False:
            self.activation_timer()

    async def event_ready(self):
        # Print message when bot is logged in and activated.
        print('IntermissionBot is up. Power of AI to the people!')

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
        parent_dir = "C:/Users/user/PycharmProjects/twitchbot/logs/"
        child_dir = f"{channel_name}/{current_date}"
        path = os.path.join(parent_dir, child_dir)
        if os.path.exists(path) is False:
            os.makedirs(path)
        else:
            pass

        file_path = f'./logs/{channel_name}/{current_date}/{current_date}.txt'

        # Open the file using UTF-8 encoding
        with open(file_path, 'a', encoding='utf-8') as file_object:
            formatted_message = f'{current_date} {current_time} {user}: {message.content}\n'
            file_object.write(formatted_message)

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
        # Set the directory here.
        parent_dir = "C:/Users/user/PycharmProjects/twitchbot/logs/"
        child_dir = f"{channel_name}/{current_date}"
        path = os.path.join(parent_dir, child_dir)
        if os.path.exists(path) is False:
            os.makedirs(path)
        else:
            pass

        file_object = open(f'./logs/{channel_name}/{current_date}/{current_date}.txt', 'a')
        file_object.write(f'{current_date} {current_time} {username} joined channel {channel_name} \n')
        file_object.close()

    @commands.command()
    async def about(self, ctx: commands.Context):
        # This gives a description of the bot
        if self.get_activation() is False:
            return
        else:
            channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

            if 'isLiveBroadcast' in channel_contents:
                print(ctx.channel.name + "is live")
                return
            else:
                await ctx.send("Hey there, lovely viewers! HeyGuys I am a ChatGPT 3.5 Turbo-powered offline chatbot, here to make your Twitch experience even more exciting and interactive! Ask me for a joke, trivia, a short story, or the benefits of touching grass!")
                self.set_activation(False)

    @commands.command()
    async def make(self, ctx: commands.Context):
        # Returns an AI generated image
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        response = openai.Image.create(
            prompt=ctx.message.content,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']

        await ctx.send(image_url)
        self.set_activation(False)

    @commands.command()
    async def inputs(self, ctx: commands.Context):
        # Lists the commands that the chatbot can use
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        await ctx.send("$about, $inputs, $nickname, $story, $touchgrass, $trivia")
        self.set_activation(False)

    @commands.command()
    async def joke(self, ctx: commands.Context):
        # This tells a chatGPT powered joke
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        number = random.randrange(0, 3)
        text_to_send = ""

        if number == 0:
            text_to_send = "Hi chat, tell me a new joke"
        elif number == 1:
            text_to_send = "Hi chat, tell me a funny joke"
        else:
            text_to_send = "Hi chat, tell me an original joke"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": text_to_send}
            ]
        )
        response_message = response['choices'][0]['message']['content']

        await ctx.send(response_message)
        self.set_activation(False)

    @commands.command()
    async def nickname(self, ctx: commands.Context):
        # Gives the user a random nickname chosen by chatGPT
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Hi chat, give me a random nickname"}
            ]
        )
        response_message = response['choices'][0]['message']['content']

        await ctx.send(response_message)
        self.set_activation(False)

    @commands.command()
    async def story(self, ctx: commands.Context):
        # Gives the user a random nickname chosen by chatGPT
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Hi chat, can you tell me a story in 150 characters or less?"}
            ]
        )
        response_message = response['choices'][0]['message']['content']

        await ctx.send(response_message)
        self.set_activation(False)

    @commands.command()
    async def touchgrass(self, ctx: commands.Context):
        # This gives a description of the bot
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        await ctx.send("Touching grass boosts mood, reduces stress, connects to nature. 8-) ")
        self.set_activation(False)

    @commands.command()
    async def trivia(self, ctx: commands.Context):
        # This tells chatGPT trivia
        if self.get_activation() is False:
            return

        channel_contents = requests.get('https://www.twitch.tv/' + ctx.channel.name).content.decode('utf-8')

        if 'isLiveBroadcast' in channel_contents:
            print(ctx.channel.name + "is live")
            return

        number = random.randrange(0, 5)
        text_to_send = ""

        if number == 0:
            text_to_send = "Hi chat, tell me some history trivia in 150 characters or less"
        elif number == 1:
            text_to_send = "Hi chat, tell me some internet trivia in 150 characters or less"
        elif number == 2:
            text_to_send = "Hi chat, tell me some culture trivia in 150 characters or less"
        elif number == 3:
            text_to_send = "Hi chat, tell me some pop culture trivia in 150 characters or less"
        elif number == 4:
            text_to_send = "Hi chat, tell me some movie trivia in 150 characters or less"
        else:
            text_to_send = "Hi chat, tell me some Twitch trivia in 150 characters or less"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": text_to_send}
            ]
        )
        response_message = response['choices'][0]['message']['content']

        await ctx.send(response_message)
        self.set_activation(False)


if __name__ == '__main__':
    ai_bot = IntermissionBot()
    ai_bot.run()
