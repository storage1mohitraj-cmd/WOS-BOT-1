import logging
from discord import app_commands, Interaction, Embed
import requests
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Timeline data extracted from https://whiteoutsurvival.pl/state-timeline/
TIMELINE_DATA = [
    {"day": 0, "event": "Initial Heroes", "description": "Game start with initial heroes"},
    {"day": 14, "event": "Tundra", "description": "Opened Tundra territory for Alliances"},
    {"day": 34, "event": "Arena opponent Update", "description": "Opponent pool enlarged by nearby servers"},
    {"day": 39, "event": "Fertile Land", "description": "Opened Fertile Land"},
    {"day": 40, "event": "Gen 2 Heroes", "description": "Alonso, Flint, Philly released"},
    {"day": 53, "event": "Sunfire Castle", "description": "Sunfire Castle becomes the battleground for state alliances"},
    {"day": 54, "event": "First Pets Update", "description": "Musk Ox, Arctic Wolf, Cave Hyena unlocked"},
    {"day": 60, "event": "Fire Crystal Age", "description": "Fire Crystal 1-3 unlocked"},
    {"day": 80, "event": "SVS and KOI", "description": "State of Power (SVS) and King of Icefield events begin"},
    {"day": 90, "event": "Second Pets Update", "description": "Titan Roc, Giant Tapir unlocked"},
    {"day": 120, "event": "Gen 3 Heroes", "description": "Greg, Logan, Mia released"},
    {"day": 140, "event": "Third Pets Update", "description": "Giant Elk, Snow Leopard unlocked"},
    {"day": 150, "event": "Crystal Infrastructure", "description": "Fire Crystal 4-5 and Crystal laboratory unlock"},
    {"day": 180, "event": "Legendary Equipment", "description": "Chief Legendary Gear Unlock"},
    {"day": 195, "event": "Gen 4 Heroes", "description": "Ahmose, Lynn, Reina released"},
    {"day": 200, "event": "Fourth Pets Update", "description": "Snow Ape, Cave Lion unlocked"},
    {"day": 220, "event": "War Academy Update", "description": "War Academy, Fire Crystal Tech and T11 Troops"},
    {"day": 270, "event": "Gen 5 Heroes", "description": "Gwen, Hector, Norah released"},
    {"day": 280, "event": "Fifth Pets Update", "description": "Iron Rhino, Saber-tooth Tiger unlocked"},
    {"day": 315, "event": "Advanced Crystal Update", "description": "Fire Crystal 6-8 and Refined Fire Crystal"},
    {"day": 360, "event": "Gen 6 Heroes", "description": "Renee, Wayne, Wuming released"},
    {"day": 370, "event": "Mammoth Update", "description": "Mammoth pet unlocked"},
    {"day": 440, "event": "Gen 7 Heroes", "description": "Bradley, Edith, Gordon released"},
    {"day": 500, "event": "Crystal Mastery", "description": "Fire Crystal 9-10 unlock"},
    {"day": 520, "event": "Gen 8 Heroes", "description": "Gatot, Hendrik, Sonya released"},
    {"day": 600, "event": "Gen 9 Heroes", "description": "Fred, Magnus, Xura released"},
    {"day": 700, "event": "Gen 10 Heroes", "description": "Blanchette, Freya, Gregory released"},
    {"day": 800, "event": "Gen 11 Heroes", "description": "Eleonora Gold, Lloyd, Rufus released"},
    {"day": 870, "event": "Gen 12 Heroes", "description": "Ligeia, Karol, Hervor released"},
    {"day": 951, "event": "Gen 13 Heroes", "description": "Gisela, Flora, Vulcanus released"},
]

def get_next_milestone(current_day):
    """Get the next milestone and days until it"""
    for milestone in TIMELINE_DATA:
        if milestone["day"] > current_day:
            days_until = milestone["day"] - current_day
            return milestone, days_until
    return None, None

def get_recent_milestones(current_day, count=3):
    """Get the most recent milestones"""
    recent = [m for m in TIMELINE_DATA if m["day"] <= current_day]
    return recent[-count:] if recent else []

def calculate_server_age_from_date(server_date_str):
    """
    Calculate server age based on a date or game launch reference.
    Attempts to parse the date and calculate days since.
    """
    try:
        # Try common date formats
        for date_format in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"]:
            try:
                server_date = datetime.strptime(server_date_str.strip(), date_format)
                days_passed = (datetime.now() - server_date).days
                return max(0, days_passed)  # Ensure non-negative
            except ValueError:
                continue
        return None
    except Exception as e:
        logger.error(f"Error calculating server age: {e}")
        return None

def setup_server_age_commands(bot):
    """Set up the server age command for the bot"""

    @bot.tree.command(name="server_age", description="Check your server age and upcoming milestones")
    @app_commands.describe(days="Number of days since server launch (or use 0 for current day reference)")
    async def server_age(interaction: Interaction, days: int = None):
        """Handle the server age command"""
        logger.info(f"Server age command called with days: {days}")

        # If no days provided, provide instructions
        if days is None:
            await interaction.response.send_message(
                "📋 **Server Age Command Usage:**\n\n"
                "Use `/server_age days:<number>` to check your server's age and milestones.\n\n"
                "**Example:** `/server_age days:120`\n\n"
                "This will show you:\n"
                "✅ Current server day\n"
                "🎯 Next major milestone\n"
                "📜 Recent milestones reached\n"
                "🌟 Upcoming features\n\n"
                "[Check your exact server age here](https://whiteoutsurvival.pl/state-timeline/)",
                ephemeral=True,
            )
            return

        # Validate input
        if days < 0:
            await interaction.response.send_message(
                "❌ Server age cannot be negative! Please enter a valid number of days.",
                ephemeral=True,
            )
            return

        # Get next milestone
        next_milestone, days_until = get_next_milestone(days)
        recent_milestones = get_recent_milestones(days)

        # Create embed
        embed = Embed(
            title="🌍 Server Age Information",
            description=f"Your server is currently on **Day {days}** of the game",
            color=0x87CEEB,
        )

        # Add current day info
        weeks = days // 7
        embed.add_field(
            name="⏱️ Server Age",
            value=f"**{days}** days (~{weeks} weeks)",
            inline=False,
        )

        # Add next milestone
        if next_milestone:
            embed.add_field(
                name="🎯 Next Milestone",
                value=f"**Day {next_milestone['day']}**: {next_milestone['event']}\n"
                      f"Coming in **{days_until}** days\n"
                      f"_{next_milestone['description']}_",
                inline=False,
            )
        else:
            embed.add_field(
                name="🎯 Next Milestone",
                value="🏆 You've reached the end of the current timeline!",
                inline=False,
            )

        # Add recent milestones
        if recent_milestones:
            recent_text = "\n".join([
                f"• **Day {m['day']}**: {m['event']}"
                for m in recent_milestones
            ])
            embed.add_field(
                name="📜 Recent Milestones",
                value=recent_text,
                inline=False,
            )

        # Add helpful links
        embed.add_field(
            name="📚 Resources",
            value="[Full State Timeline](https://whiteoutsurvival.pl/state-timeline/)\n"
                  "[Whiteout Survival Official](https://whiteoutsurvival.pl/)",
            inline=False,
        )

        embed.set_footer(text="Use /server_age to check your server's milestones | Last updated: 2025-11-12")

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="timeline", description="View the complete Whiteout Survival game timeline")
    async def timeline(interaction: Interaction):
        """Show the complete game timeline"""
        logger.info("Timeline command called")

        # Create multiple embeds if needed (Discord has character limits)
        embeds = []

        # First embed - overview
        overview_embed = Embed(
            title="🌍 Complete Whiteout Survival Timeline",
            description="Here's what unlocks as your server ages",
            color=0x87CEEB,
        )
        overview_embed.add_field(
            name="📊 Total Milestones",
            value=f"{len(TIMELINE_DATA)} major events tracked",
            inline=True,
        )
        overview_embed.add_field(
            name="🎮 Latest Gen",
            value="Gen 13 Heroes at Day 951",
            inline=True,
        )
        embeds.append(overview_embed)

        # Timeline embeds (split into chunks of 5-6 milestones)
        chunk_size = 6
        for i in range(0, len(TIMELINE_DATA), chunk_size):
            chunk = TIMELINE_DATA[i:i+chunk_size]
            embed = Embed(
                title=f"Timeline - Part {i//chunk_size + 1}",
                color=0x87CEEB,
            )

            for milestone in chunk:
                embed.add_field(
                    name=f"Day {milestone['day']}: {milestone['event']}",
                    value=milestone['description'],
                    inline=False,
                )

            embeds.append(embed)

        # Source embed
        source_embed = Embed(
            title="📖 Source",
            description="Timeline data extracted from [Whiteout Survival State Timeline](https://whiteoutsurvival.pl/state-timeline/)",
            color=0x87CEEB,
        )
        source_embed.set_footer(text="Last updated: 2025-11-12")
        embeds.append(source_embed)

        # Send embeds
        await interaction.response.send_message(embeds=embeds)
