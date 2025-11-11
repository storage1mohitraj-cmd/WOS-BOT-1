import discord
from discord.ext import commands
import asyncio

class OtherFeatures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def show_other_features_menu(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="🔧 Other Features",
                description=(
                    "Select one of the following features:\n\n"
                    "• Bear Trap Notifications\n"
                    "• ID Channel Registration\n"
                    "• Minister Scheduling\n"
                    "• Backup System\n"
                    "• Attendance System\n\n"
                    "Click a button below to open the corresponding configuration menu."
                ),
                color=discord.Color.blue()
            )

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Bear Trap", emoji="🪤", style=discord.ButtonStyle.primary, custom_id="bear_trap"))
            view.add_item(discord.ui.Button(label="ID Channel", emoji="🔐", style=discord.ButtonStyle.primary, custom_id="id_channel"))
            view.add_item(discord.ui.Button(label="Minister Scheduling", emoji="📅", style=discord.ButtonStyle.primary, custom_id="minister_scheduling"))
            view.add_item(discord.ui.Button(label="Backups", emoji="💾", style=discord.ButtonStyle.primary, custom_id="backups"))
            view.add_item(discord.ui.Button(label="Attendance", emoji="🧾", style=discord.ButtonStyle.primary, custom_id="attendance"))
            view.add_item(discord.ui.Button(label="Main Menu", emoji="🏠", style=discord.ButtonStyle.secondary, custom_id="main_menu"))

            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error showing other features menu: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred while opening Other Features.", ephemeral=True)
                else:
                    await interaction.followup.send("An error occurred while opening Other Features.", ephemeral=True)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get('custom_id')

        try:
            if custom_id == 'bear_trap':
                cog = self.bot.get_cog('BearTrap') or self.bot.get_cog('bear_trap')
                if cog and hasattr(cog, 'show_bear_trap_menu'):
                    await cog.show_bear_trap_menu(interaction)
                else:
                    await interaction.response.send_message('Bear Trap module not found.', ephemeral=True)

            elif custom_id == 'id_channel':
                cog = self.bot.get_cog('IDChannel') or self.bot.get_cog('id_channel')
                if cog and hasattr(cog, 'show_id_channel_menu'):
                    await cog.show_id_channel_menu(interaction)
                else:
                    await interaction.response.send_message('ID Channel module not found.', ephemeral=True)

            elif custom_id == 'minister_scheduling':
                cog = self.bot.get_cog('MinisterMenu') or self.bot.get_cog('minister_menu')
                if cog and hasattr(cog, 'show_settings_menu'):
                    await cog.show_settings_menu(interaction)
                else:
                    await interaction.response.send_message('Minister Scheduling module not found.', ephemeral=True)

            elif custom_id == 'backups':
                cog = self.bot.get_cog('BackupOperations') or self.bot.get_cog('backup_operations')
                if cog and hasattr(cog, 'show_backup_menu'):
                    await cog.show_backup_menu(interaction)
                else:
                    await interaction.response.send_message('Backup module not found.', ephemeral=True)

            elif custom_id == 'attendance':
                cog = self.bot.get_cog('Attendance') or self.bot.get_cog('attendance')
                if cog and hasattr(cog, 'show_attendance_menu'):
                    await cog.show_attendance_menu(interaction)
                else:
                    await interaction.response.send_message('Attendance module not found.', ephemeral=True)

            elif custom_id == 'main_menu':
                alliance_cog = self.bot.get_cog('Alliance')
                if alliance_cog and hasattr(alliance_cog, 'show_main_menu'):
                    await alliance_cog.show_main_menu(interaction)
                else:
                    await interaction.response.send_message('Main settings module not found.', ephemeral=True)

        except Exception as e:
            print(f"Error in OtherFeatures on_interaction: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message('An unexpected error occurred.', ephemeral=True)
                else:
                    await interaction.followup.send('An unexpected error occurred.', ephemeral=True)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(OtherFeatures(bot))
