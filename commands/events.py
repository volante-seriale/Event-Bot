import zoneinfo
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

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
    )
    async def create_event(
        self,
        interaction: discord.Interaction,
        name: str,
        date: str,
        time_utc: str,
        build: str,
        mention_role: discord.Role = None,
    ):
        # 1. Validazione della data e ora
        try:
            full_dt_str = f"{date} {time_utc}"
            dt_obj = datetime.strptime(full_dt_str, "%d/%m/%Y %H:%M")
            dt_obj = dt_obj.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
            unix_timestamp = int(dt_obj.timestamp())
            timestamp_display = f"<t:{unix_timestamp}:t>"
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid format! Use DD/MM/YYYY and HH:MM.", ephemeral=True
            )
            return

        # Mandiamo la risposta iniziale per evitare il timeout di 3 secondi di Discord
        await interaction.response.send_message(
            f"Creating thread for event: **{name}**...", ephemeral=True
        )

        # 2. Controllo dei permessi del canale prima di procedere
        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            await interaction.edit_original_response(
                content="❌ Events can only be created in standard text or voice channels."
            )
            return

        try:
            # CORREZIONE: Creazione corretta del thread senza passare 'type' non necessario
            thread = await channel.create_thread(
                name=f"📅 {name} | {date} at {time_utc} UTC",
                auto_archive_duration=1440,  # 24 ore
            )

            build_list = [item.strip() for item in build.split(";") if item.strip()]
            
            embed = discord.Embed(
                title=name,
                description=f"**Date**: {date} | **Time**: {timestamp_display}",
                color=discord.Color.gold(),
            )

            initial_comp = "\n".join(
                [f"**{i + 1}\\. {role}**: ---" for i, role in enumerate(build_list)]
            )
            embed.add_field(name="Composition", value=initial_comp, inline=False)
            
            content_str = mention_role.mention if mention_role else ""
            
            # Inviamo il messaggio dentro al thread appena creato
            msg = await thread.send(
                content=content_str,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True) if mention_role else discord.AllowedMentions.none(),
            )

            event_data = {
                "name": name,
                "creator_id": interaction.user.id,
                "build_list": build_list,
                "participants": {},
            }

            # Salvataggio DB e attivazione della View dei bottoni
            save_event(msg.id, event_data)
            view = EventView(event_id=msg.id, event_data=event_data)
            await msg.edit(view=view)
            
            # Conferma finale all'utente
            await interaction.edit_original_response(
                content=f"✅ Event thread created successfully: {thread.mention}"
            )

        except discord.Forbidden:
            # Gestione errore nel caso in cui il bot non abbia i permessi nel canale
            await interaction.edit_original_response(
                content="❌ I don't have permission to create threads or send messages in this channel."
            )
        except Exception as e:
            # Qualsiasi altro errore imprevisto
            await interaction.edit_original_response(
                content=f"❌ An unexpected error occurred: {str(e)}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))