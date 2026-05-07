import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from datetime import datetime
import zoneinfo

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
    
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class EventBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=intents)
        self.active_event_id = None

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced commands for {self.user}.")
    
    async def on_ready(self):
        print(f"{self.user} has connected to Discord!")
bot = EventBot()

# --- Role Selection ---
class RoleSelect(discord.ui.Select):
    def __init__(self, parent_view, build_list):
        self.parent_view = parent_view
        options = [discord.SelectOption(label=f"{i+1}: {role}", value=str(i)) for i, role in enumerate(build_list)]
        super().__init__(placeholder="Select your role", options=options)
        
    async def callback(self, interaction: discord.Interaction):
        slot_index = int(self.values[0])
        user_id = interaction.user.id
        
        self.parent_view.participants_roles[user_id] = slot_index
        
        original_msg = interaction.message.reference.cached_message
        if not original_msg: # Fallback if message not in cache
            original_msg = await interaction.channel.fetch_message(interaction.message.reference.message_id)
            
        new_embed = self.parent_view.update_embed(original_msg.embeds[0])
        await original_msg.edit(embed=new_embed, view=self.parent_view)
        await interaction.response.send_message(f"You have selected: {self.options[slot_index].label}", ephemeral=True)

# --- UI components ---
class EventView(discord.ui.View):
    def __init__(self, bot_instance, creator_id, event_name, build_list):
        super().__init__(timeout=None)
        self.bot = bot_instance
        self.creator_id = creator_id
        self.event_name = event_name
        self.build_list = build_list 
        self.participants_roles = {} 
        
    def update_embed(self, embed: discord.Embed):
        composition_lines = []
        for i, role_name in enumerate(self.build_list):
            occupants = [f"<@{uid}>" for uid, slot in self.participants_roles.items() if slot == i]
            user_display = ", ".join(occupants) if occupants else "---"
            composition_lines.append(f"**{i+1}\\. {role_name}**: {user_display}")
            
        new_value = "\n".join(composition_lines)
        embed.set_field_at(0, name="Composition", value=new_value, inline=False)
        return embed
        
    @discord.ui.button(label="Sign-Up", style=discord.ButtonStyle.green)
    async def sign_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        select_view = discord.ui.View()
        select_view.add_item(RoleSelect(self, self.build_list))
        await interaction.response.send_message("Select your role:", view=select_view, ephemeral=True)
        
    @discord.ui.button(label="Sign-Off", style=discord.ButtonStyle.red)
    async def sign_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participants_roles:
            del self.participants_roles[interaction.user.id]
            
        new_embed = self.update_embed(interaction.message.embeds[0])
        await interaction.response.edit_message(embed=new_embed, view=self)
        
    @discord.ui.button(label="Ping", style= discord.ButtonStyle.blurple)
    async def ping_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_creator = interaction.user.id == self.creator_id
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_creator or is_admin):
            await interaction.response.send_message("Only the event creator and administrators can ping participants.", ephemeral=True)
            return
        
        if not self.participants_roles:
            await interaction.response.send_message("No participants to ping!", ephemeral=True)
            return

        mentions = " ".join([f"<@{uid}>" for uid in self.participants_roles.keys()])
        await interaction.response.send_message(f"Ping: {mentions}", ephemeral=False)
        
    @discord.ui.button(label="End Event", style=discord.ButtonStyle.gray)
    async def end_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_creator = interaction.user.id == self.creator_id
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_creator or is_admin):
            await interaction.response.send_message("Only the event creator and administrators can end the event.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.bot.active_event_id = None
        await interaction.followup.send(f"The event '{self.event_name}' has ended.", ephemeral=False)

# --- Commands ---
@bot.tree.command(name="create_event", description="Create a new event.")
@app_commands.describe(
    name="Name of the event",
    date="Date of the event (DD/MM/YYYY)",
    time_utc="Time of the event (HH:MM)",
    build="Composition with ';' between weapons (Tank;Healer;DPS1;DPS2)",
    mention_role="Role to mention when announcing the event"
)
async def create_event(
    interaction: discord.Interaction, 
    name: str,
    date: str,
    time_utc: str,
    build: str,
    mention_role: discord.Role
    ):
    if bot.active_event_id is not None:
        await interaction.response.send_message("⚠️ An event is already active!", ephemeral=True)
        return
    
    try:
        full_dt_str = f"{date} {time_utc}"
        dt_obj = datetime.strptime(full_dt_str, "%d/%m/%Y %H:%M")
        dt_obj = dt_obj.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        unix_timestamp = int(dt_obj.timestamp())
        timestamp_display = f"<t:{unix_timestamp}:t>"
    except ValueError:
        await interaction.response.send_message("❌ Invalid date/time format! Use DD/MM/YYYY for date and HH:MM for time.", ephemeral=True)
        return
    
    build_list = [item.strip() for item in build.split(";")]
    
    embed = discord.Embed(
        title=name,
        description=f"**Date**: {date} | **Time**: {timestamp_display}",
        color=discord.Color.gold()
    )
    
    initial_comp = "\n".join([f"**{i+1}\\. {role}**: ---" for i, role in enumerate(build_list)])
    embed.add_field(name="Composition", value=initial_comp, inline=False)
    
    view = EventView(bot_instance=bot, creator_id=interaction.user.id, event_name=name, build_list=build_list)
    await interaction.response.send_message(content=mention_role.mention, embed=embed, view=view)

    original_message = await interaction.original_response()
    bot.active_event_id = original_message.id

bot.run(TOKEN)