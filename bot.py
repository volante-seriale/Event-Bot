import discord
from discord.ext import commands

from config import TOKEN, intents
from db import init_db, load_all_events
from ui.event_view import EventView


class EventBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=intents)

    async def setup_hook(self):
        init_db()
        events = load_all_events()

        for msg_id, data in events.items():
            self.add_view(EventView(event_id=msg_id, event_data=data))

        await self.load_extension("commands.events")
        await self.tree.sync()
        print(f"Synced commands and restored {len(events)} events.")

    async def on_ready(self):
        print(f"{self.user} is online and ready!")


bot = EventBot()
bot.run(TOKEN)
