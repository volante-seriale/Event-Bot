import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

DB_PATH = "data/events.db"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
