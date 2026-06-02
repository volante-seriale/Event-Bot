import discord

from db import delete_event, save_event
from ui.role_select import RoleSelect


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
            composition_lines.append(f"**{i + 1}\\. {role_name}**: {user_display}")

        new_value = "\n".join(composition_lines)
        embed.set_field_at(0, name="Composition", value=new_value, inline=False)
        return embed

    @discord.ui.button(
        label="Sign-Up", style=discord.ButtonStyle.green, custom_id="evt:signup"
    )
    async def sign_up(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        select_view = discord.ui.View()
        select_view.add_item(RoleSelect(self, self.event_data["build_list"]))
        await interaction.response.send_message(
            "Select your role:", view=select_view, ephemeral=True
        )

    @discord.ui.button(
        label="Sign-Off", style=discord.ButtonStyle.red, custom_id="evt:signoff"
    )
    async def sign_off(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)
        if user_id in self.event_data["participants"]:
            del self.event_data["participants"][user_id]
            save_event(self.event_id, self.event_data)

            new_embed = self.update_embed(interaction.message.embeds[0])
            await interaction.response.edit_message(embed=new_embed, view=self)
            await interaction.followup.send("You have signed off.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "You are not in this event.", ephemeral=True
            )

    @discord.ui.button(
        label="Ping", style=discord.ButtonStyle.blurple, custom_id="evt:ping"
    )
    async def ping_participants(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
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

    @discord.ui.button(
        label="End Event", style=discord.ButtonStyle.gray, custom_id="evt:end"
    )
    async def end_event(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        is_creator = interaction.user.id == self.event_data["creator_id"]
        is_admin = interaction.user.guild_permissions.administrator

        if not (is_creator or is_admin):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        delete_event(self.event_id)

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"The event '{self.event_data['name']}' has ended."
        )
