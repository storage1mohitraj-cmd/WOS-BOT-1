"""Minimal Gift Operations cog with Redeem Latest (Alliance) button.

This file provides a small, self-contained implementation that fits the
request: the "Redeem Latest (Alliance)" button lives inside the GiftView
and uses the specified SQL selection, presents an ALL option, calls
add_manual_redemption_to_queue and get_queue_status.

If you prefer the full canonical implementation, we can replace this file
with the larger, feature-complete version and carefully merge local helpers.
"""

import discord
from discord.ext import commands
import sqlite3
import os
import logging
from datetime import datetime


class GiftOperations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('gift_ops')

        if not os.path.exists('db'):
            os.makedirs('db')

        self.conn = sqlite3.connect('db/giftcode.sqlite')
        self.cursor = self.conn.cursor()

        # Minimal tables used by the UI flow
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gift_codes (
                giftcode TEXT PRIMARY KEY,
                date TEXT,
                validation_status TEXT DEFAULT 'pending'
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS alliance_list (
                alliance_id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giftcode TEXT,
                alliance_id INTEGER,
                queued_at TEXT
            )
        """)
        self.conn.commit()

    async def add_manual_redemption_to_queue(self, giftcode, alliance_ids, interaction=None):
        positions = []
        try:
            for aid in alliance_ids:
                now = datetime.utcnow().isoformat()
                self.cursor.execute(
                    "INSERT INTO manual_redemptions (giftcode, alliance_id, queued_at) VALUES (?, ?, ?)",
                    (giftcode, aid, now),
                )
                self.conn.commit()
                self.cursor.execute("SELECT COUNT(*) FROM manual_redemptions WHERE giftcode = ?", (giftcode,))
                positions.append(self.cursor.fetchone()[0])
        except Exception as e:
            self.logger.exception(f"Error queueing manual redemption: {e}")
        return positions

    async def get_queue_status(self):
        try:
            self.cursor.execute(
                "SELECT giftcode, COUNT(*) as cnt FROM manual_redemptions GROUP BY giftcode ORDER BY MAX(queued_at) DESC"
            )
            rows = self.cursor.fetchall()
            queue_by_code = {r[0]: [{'position': r[1]}] for r in rows}
            self.cursor.execute("SELECT COUNT(*) FROM manual_redemptions")
            total = self.cursor.fetchone()[0]
            return {
                'queue_length': total,
                'processing': False,
                'items': [{'giftcode': r[0], 'count': r[1]} for r in rows],
                'queue_by_code': queue_by_code,
            }
        except Exception as e:
            self.logger.exception(f"Error getting queue status: {e}")
            return {'queue_length': 0, 'processing': False, 'items': [], 'queue_by_code': {}}

    async def show_gift_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎁 Gift Code Operations", description="Select an operation below.")
        view = GiftView(self)
        try:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            except Exception:
                pass


class GiftView(discord.ui.View):
    def __init__(self, cog: GiftOperations):
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(label="Redeem Latest (Alliance)", style=discord.ButtonStyle.primary, custom_id="redeem_latest_alliance")
    async def redeem_latest_alliance(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get the latest non-invalid gift code
            self.cog.cursor.execute(
                "SELECT giftcode FROM gift_codes WHERE validation_status != 'invalid' ORDER BY date DESC LIMIT 1"
            )
            row = self.cog.cursor.fetchone()
            if not row:
                await interaction.response.send_message("No active gift codes found.", ephemeral=True)
                return
            latest_code = row[0]

            # Load alliances
            self.cog.cursor.execute("SELECT alliance_id, name FROM alliance_list ORDER BY name ASC")
            alliances = self.cog.cursor.fetchall()
            if not alliances:
                await interaction.response.send_message("No alliances configured.", ephemeral=True)
                return

            options = [discord.SelectOption(label="ALL ALLIANCES", value="all", description="Apply to all alliances")]
            for aid, name in alliances:
                options.append(discord.SelectOption(label=name, value=str(aid)))

            select = discord.ui.Select(placeholder="Select alliance(s)", min_values=1, max_values=1, options=options)

            async def select_callback(select_interaction: discord.Interaction):
                try:
                    val = select.values[0]
                    if val == 'all':
                        alliance_ids = [aid for aid, _ in alliances]
                    else:
                        alliance_ids = [int(val)]

                    await select_interaction.response.defer(ephemeral=True)
                    await self.cog.add_manual_redemption_to_queue(latest_code, alliance_ids, select_interaction)
                    queue_status = await self.cog.get_queue_status()

                    items = queue_status.get('items', [])
                    summary = '\n'.join([f"`{it['giftcode']}` - {it.get('count', 0)} queued" for it in items]) or "Queue is empty"
                    embed = discord.Embed(title="✅ Redemptions Queued", description=f"**Code:** `{latest_code}`\n\n{summary}")
                    await select_interaction.followup.send(embed=embed, ephemeral=True)
                except Exception as e:
                    self.cog.logger.exception(f"Error in redeem latest select callback: {e}")
                    try:
                        await select_interaction.followup.send("An error occurred.", ephemeral=True)
                    except Exception:
                        pass

            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)
            await interaction.response.send_message("Please choose an alliance:", view=view, ephemeral=True)

        except Exception as e:
            self.cog.logger.exception(f"Error in redeem_latest_alliance button: {e}")
            try:
                await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(GiftOperations(bot))
