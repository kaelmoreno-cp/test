"""
Cathy AI Discord Chat Bot
Written in Python 3 using AIML chat library.
"""
import discord
import os
import random
import pkg_resources
from discord.ext import commands
import asyncio
import aiml
import time


STARTUP_FILE = "std-startup.xml"
BOT_PREFIX = ('?')

def _log(message):
    print(time.strftime("%Y %b %d %H:%M:%S") + ": " + str(message))

class ChattyCathy:
    """
    Class that contains all of the bot logic
    """
    
    def __init__(self, bot_token):
        """
        Initialize the bot using the Discord token and channel name to chat in.
        :param channel_name: Only chats in this channel. No hashtag included.
        :param bot_token: Full secret bot token
        """
        self.token = bot_token

        # Load AIML kernel
        self.aiml_kernel = aiml.Kernel()
        # initial_dir = os.getcwd()
        # os.chdir(pkg_resources.resource_filename(__name__, ''))  # Change directories to load AIML files properly
        startup_filename = pkg_resources.resource_filename(__name__, STARTUP_FILE)
        self.aiml_kernel.learn(startup_filename)
        self.aiml_kernel.respond("LOAD AIML B")
        # os.chdir(initial_dir)

        # Set up Discord client
        self.discord_client = commands.Bot(command_prefix=BOT_PREFIX)
        self.setup()

    def setup(self):

        @self.discord_client.event
        @asyncio.coroutine
        def on_ready():
            print("Bot Online!")
            print("Name: {}".format(self.discord_client.user.name))
            print("ID: {}".format(self.discord_client.user.id))
            yield from self.discord_client.change_presence(game=discord.Game(name='Chatting with Humans'))

        @self.discord_client.event
        @asyncio.coroutine
        def on_message(message):
            if message.author.bot:
                return

            if message.content is None:
                return

            s = message.content.split()

            if len(s) < 2:
                return

            if s[0].lower() == "?kukui":
                question = " ".join(s[1:])
                aiml_response = self.aiml_kernel.respond(question)
                _log("\nQ: " + question + "\nA: " + aiml_response)
                if aiml_response:
                    yield from self.discord_client.send_typing(message.channel)
                    yield from asyncio.sleep(random.randint(1,3))
                    yield from self.discord_client.send_message(message.channel, aiml_response)

    def run(self):
        self.discord_client.run(self.token)

bot = ChattyCathy("XXX")
bot.run()
