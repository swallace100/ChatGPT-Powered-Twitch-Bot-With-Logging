# Get Twitch Access Token at https://twitchtokengenerator.com/
from twitchio.ext import commands
from datetime import datetime
from dotenv import load_dotenv
import requests
import random
import os
import openai
import threading

# This is the class for the bot. Only one class can be active at once.
# This is an offline chat bot and will only work when a streamer is offline.
class IntermissionBot(commands.Bot):

    # Get the environment variables
    load_dotenv("resources/appSettings.env")

    openai.api_key = os.getenv("OPENAI_API_KEY")

    def __init__(self):

        # --- helpers ---
        def _split_list(val: str, default: str = ""):
            raw = (val or default).replace(";", ",")
            return [x.strip() for x in raw.split(",") if x.strip()]

        def _channels(val: str):
            return [c.lstrip("#").lower() for c in _split_list(val)]

        # --- read settings ---
        token_env = os.getenv("TWITCH_ACCESS_TOKEN", "")
        token = token_env if token_env.startswith("oauth:") else f"oauth:{token_env}"

        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")  # may be empty if using device flow only
        bot_id = os.getenv("TWITCH_BOT_ID")
        prefixes = _split_list(os.getenv("PREFIX"), "$") or ["$"]
        channels = _channels(os.getenv("INITIAL_CHANNELS"))
        log_dir = os.getenv("LOG_DIRECTORY", "logs")

        # --- basic validation ---
        if not client_id:
            raise ValueError("TWITCH_CLIENT_ID is required.")
        if not token_env:
            raise ValueError("TWITCH_ACCESS_TOKEN is required.")
        if not bot_id:
            raise ValueError("TWITCH_BOT_ID is required.")
        if not channels:
            raise ValueError("INITIAL_CHANNELS is empty. Provide at least one channel (comma-separated).")

        super().__init__(
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            prefix=prefixes
        )

        self._active = True
        self.log_directory=log_dir

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
        print(f"Logged in as: {self.user.name} (id: {self.user.id})")

    async def event_message(self, message):
        print("Message received")
        if message.echo:
            return

        # Let TwitchIO's command processor run
        await super().event_message(message)

        user = message.author.name
        channel_name = message.channel.name

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date_str = str(now.date())

        print(f"{current_date_str} {current_time} {user}: {message.content}")

        # Build log path relative to configured LOG_DIRECTORY
        path = os.path.join(self.log_directory, channel_name, current_date_str)
        os.makedirs(path, exist_ok=True)

        file_path = os.path.join(path, f"{current_date_str}.txt")

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{current_date_str} {current_time} {user}: {message.content}\n")

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
        parent_dir = self.log_directory
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
            model="gpt-4o",
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
