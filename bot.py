import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import zoneinfo

# --- Configurazione Iniziale ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

FILE_PATH = "data/events.json"

# --- Utility per il JSON ---
def _write_json(data):
folder = os.path.dirname(FILE_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(dir=folder, text=True)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, FILE_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

def load_events():
    try:
        with open(FILE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_event_data(message_id, data):
    events = load_events()
    events[str(message_id)] = data
    _write_json(events)

def delete_event_data(message_id):
    events = load_events()
    msg_id_str = str(message_id)
    if msg_id_str in events:
        del events[msg_id_str]
        _write_json(events)
        
# --- UI Components ---
class RoleSelect(discord.ui.Select):
    def __init__(self, parent_view, build_list):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=f"{i+1}: {role}", value=str(i)) 
            for i, role in enumerate(build_list)
        ]
        super().__init__(placeholder="Select your role", options=options)
        
    async def callback(self, interaction: discord.Interaction):
        slot_index = int(self.values[0])
        user_id = str(interaction.user.id)
        
        participants = self.parent_view.event_data["participants"]
        occupant_id = next((uid for uid, slot in participants.items() if slot == slot_index), None)

        if occupant_id is not None and occupant_id != user_id:
            await interaction.response.send_message(
                f"That role is already taken by <@{occupant_id}>.", ephemeral=True
            )
            return
        
        try:
            participants[user_id] = slot_index
            save_event_data(self.parent_view.event_id, self.parent_view.event_data)
            channel = interaction.channel
            original_msg = await channel.fetch_message(int(self.parent_view.event_id))
            new_embed = self.parent_view.update_embed(original_msg.embeds[0])
            await original_msg.edit(embed=new_embed, view=self.parent_view)
            await interaction.response.send_message(
                f"You signed up as **{self.options[slot_index].label}**.", ephemeral=True
            )
        except discord.NotFound:
            delete_event_data(self.parent_view.event_id)
            await interaction.response.send_message(
                "❌ The event no longer exists. Signup cancelled.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", ephemeral=True
            )
        participants[user_id] = slot_index
        save_event_data(self.parent_view.event_id, self.parent_view.event_data)
        
        channel = interaction.channel
        original_msg = await channel.fetch_message(int(self.parent_view.event_id))
        
        new_embed = self.parent_view.update_embed(original_msg.embeds[0])

        await interaction.followup.send(
            f"You signed up as **{self.options[slot_index].label}**.", ephemeral=True
        )

        await original_msg.edit(embed=new_embed, view=self.parent_view)

class EventView(discord.ui.View):
    def __init__(self, event_id, event_data):
        super().__init__(timeout=None)
        self.event_id = str(event_id)
        self.event_data = event_data
        
    def update_embed(self, embed: discord.Embed):
        build_list = self.event_data["build_list"]
        participants = self.event_data["participants"]
        
        composition_lines = []
        for i, role_name in enumerate(build_list):
            occupants = [f"<@{uid}>" for uid, slot in participants.items() if slot == i]
            user_display = ", ".join(occupants) if occupants else "---"
            composition_lines.append(f"**{i+1}\\. {role_name}**: {user_display}")
            
        new_value = "\n".join(composition_lines)
        embed.set_field_at(0, name="Composition", value=new_value, inline=False)
        return embed
        
    @discord.ui.button(label="Sign-Up", style=discord.ButtonStyle.green, custom_id="evt:signup")
    async def sign_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        select_view = discord.ui.View()
        select_view.add_item(RoleSelect(self, self.event_data["build_list"]))
        await interaction.response.send_message("Select your role:", view=select_view, ephemeral=True)
        
    @discord.ui.button(label="Sign-Off", style=discord.ButtonStyle.red, custom_id="evt:signoff")
    async def sign_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        if user_id in self.event_data["participants"]:
            del self.event_data["participants"][user_id]
            save_event_data(self.event_id, self.event_data)
            
            new_embed = self.update_embed(interaction.message.embeds[0])
            await interaction.response.edit_message(embed=new_embed, view=self)
            await interaction.followup.send("You have signed off.", ephemeral=True)
        else:
            await interaction.response.send_message("You are not in this event.", ephemeral=True)
        
    @discord.ui.button(label="Ping", style=discord.ButtonStyle.blurple, custom_id="evt:ping")
    async def ping_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_creator = interaction.user.id == self.event_data["creator_id"]
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_creator or is_admin):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        
        participants = self.event_data["participants"]
        if not participants:
            await interaction.response.send_message("No participants!", ephemeral=True)
            return

        mentions = " ".join([f"<@{uid}>" for uid in participants.keys()])
        await interaction.response.send_message(f"Ping: {mentions}", ephemeral=False)
        
    @discord.ui.button(label="End Event", style=discord.ButtonStyle.gray, custom_id="evt:end")
    async def end_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_creator = interaction.user.id == self.event_data["creator_id"]
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_creator or is_admin):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
            
        for child in self.children:
            child.disabled = True
            
        delete_event_data(self.event_id)
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"The event '{self.event_data['name']}' has ended.")

# --- Bot Class ---
class EventBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=intents)

    async def setup_hook(self):
        events = load_events()
        to_remove = []
        
        for msg_id, data in events.items():
            self.add_view(EventView(event_id=msg_id, event_data=data))
            
        await self.tree.sync()
        print(f"Synced commands and restored {len(events)} events.")
    
    async def on_ready(self):
        print(f"{self.user} is online and ready!")

bot = EventBot()

# --- Commands ---
@bot.tree.command(name="create_event", description="Create a new event.")
@app_commands.describe(
    name="Name of the event",
    date="Date (DD/MM/YYYY)",
    time_utc="Time (HH:MM)",
    build="Role list separated by ';' (e.g. Tank;Healer;DPS)",
    mention_role="Role to mention"
)
async def create_event(
    interaction: discord.Interaction, 
    name: str, 
    date: str, 
    time_utc: str, 
    build: str,
    mention_role: discord.Role = None
):
    try:
        full_dt_str = f"{date} {time_utc}"
        dt_obj = datetime.strptime(full_dt_str, "%d/%m/%Y %H:%M")
        dt_obj = dt_obj.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        unix_timestamp = int(dt_obj.timestamp())
        timestamp_display = f"<t:{unix_timestamp}:t>"
    except ValueError:
        await interaction.response.send_message("❌ Invalid format! Use DD/MM/YYYY and HH:MM.", ephemeral=True)
        return
    
    build_list = [item.strip() for item in build.split(";")]
    
    embed = discord.Embed(
        title=name,
        description=f"**Date**: {date} | **Time**: {timestamp_display}",
        color=discord.Color.gold()
    )
    
    initial_comp = "\n".join([f"**{i+1}\\. {role}**: ---" for i, role in enumerate(build_list)])
    embed.add_field(name="Composition", value=initial_comp, inline=False)
    
    content_str = mention_role.mention if mention_role else ""
    
    await interaction.response.send_message(
        content=content_str,
        embed=embed, 
        allowed_mentions=discord.AllowedMentions(roles=True) if mention_role else None
    )
    
    msg = await interaction.original_response()
    
    event_data = {
        "name": name,
        "creator_id": interaction.user.id,
        "build_list": build_list,
        "participants": {}
    }

    save_event_data(msg.id, event_data)
    view = EventView(event_id=msg.id, event_data=event_data)
    await msg.edit(view=view)
    
bot.run(TOKEN)