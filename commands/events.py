import zoneinfo
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from db import save_event
from ui.event_view import EventView


class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="create_event", description="Create a new event inside a thread."
    )
    @app_commands.describe(
        name="Name of the event",
        date="Date (DD/MM/YYYY)",
        time_utc="Time (HH:MM)",
        build="Role list separated by ';' (e.g. Tank;Healer;DPS)",
        mention_role="Role to mention",
        builds_sheet="Link to the builds sheet",
    )
    async def create_event(
        self,
        interaction: discord.Interaction,
        name: str,
        date: str,
        time_utc: str,
        build: str,
        mention_role: discord.Role,
        builds_sheet: Optional[discord.TextChannel],
    ):
        try:
            full_dt_str = f"{date} {time_utc}"
            dt_obj = datetime.strptime(full_dt_str, "%d/%m/%Y %H:%M")
            dt_obj = dt_obj.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
            unix_timestamp = int(dt_obj.timestamp())
            timestamp_display = f"<t:{unix_timestamp}:f>"
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid format! Use DD/MM/YYYY and HH:MM.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Creating thread for event: **{name}**...", ephemeral=True
        )

        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            await interaction.edit_original_response(
                content="❌ Events can only be created in standard text or voice channels."
            )
            return

        try:            
            date_str = dt_obj.strftime("%d/%m/%Y at %H:%M UTC")
            
            main_msg = await channel.send(f"📅 {name} | **<t:{unix_timestamp}:f>** - {mention_role.mention}")
            
            thread = await main_msg.create_thread(
                name=f"📅 {name} | {date_str}"[:100],
                auto_archive_duration=1440,
            )

            build_list = [item.strip() for item in build.split(";") if item.strip()]
            
            embed = discord.Embed(
                title=name,
                description=f"**When**: {timestamp_display}",
                color=discord.Color.gold(),
            )
                        
            initial_comp = "\n".join(
                [f"**{i + 1}\\. {role}**: ---" for i, role in enumerate(build_list)]
            )
            embed.add_field(name="Composition", value=initial_comp, inline=False)
                
            if builds_sheet:
                embed.add_field(name="Builds Sheet", value=builds_sheet.mention, inline=False)
        
            msg = await thread.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True) if mention_role else discord.AllowedMentions.none(),
            )

            event_data = {
                "name": name,
                "creator_id": interaction.user.id,
                "build_list": build_list,
                "participants": {},
            }

            save_event(msg.id, event_data)
            view = EventView(event_id=msg.id, event_data=event_data)
            await msg.edit(view=view)
            
            await interaction.edit_original_response(
                content=f"✅ Event thread created successfully: {thread.mention}"
            )

        except discord.Forbidden:
            await interaction.edit_original_response(
                content="❌ I don't have permission to create threads or send messages in this channel."
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ An unexpected error occurred: {str(e)}"
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))