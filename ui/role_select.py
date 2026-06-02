import discord

from db import delete_event, save_event


class RoleSelect(discord.ui.Select):
    def __init__(self, parent_view, build_list):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=f"{i + 1}: {role}", value=str(i))
            for i, role in enumerate(build_list)
        ]
        super().__init__(placeholder="Select your role", options=options)

    async def callback(self, interaction: discord.Interaction):
        slot_index = int(self.values[0])
        user_id = str(interaction.user.id)

        participants = self.parent_view.event_data["participants"]

        occupant_id = next(
            (uid for uid, slot in participants.items() if slot == slot_index), None
        )
        if occupant_id is not None and occupant_id != user_id:
            await interaction.response.send_message(
                f"That role is already taken by <@{occupant_id}>.", ephemeral=True
            )
            return

        try:
            participants[user_id] = slot_index
            save_event(self.parent_view.event_id, self.parent_view.event_data)
            channel = interaction.channel
            original_msg = await channel.fetch_message(int(self.parent_view.event_id))
            new_embed = self.parent_view.update_embed(original_msg.embeds[0])
            await original_msg.edit(embed=new_embed, view=self.parent_view)
            await interaction.response.send_message(
                f"You signed up as **{self.options[slot_index].label}**.",
                ephemeral=True,
            )
        except discord.NotFound:
            delete_event(self.parent_view.event_id)
            await interaction.response.send_message(
                "❌ The event no longer exists. Signup cancelled.", ephemeral=True
            )
        except Exception as e:
            msg = f"Error: {e}. Try again later."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
