import logging
from discord import app_commands, Interaction, Embed
from event_tips import EVENT_TIPS, get_event_info, get_all_categories, get_difficulty_color, get_category_emoji

logger = logging.getLogger(__name__)

def setup_event_commands(bot):
    """Set up the event command for the bot"""

    @bot.tree.command(name="event", description="Get information about Whiteout Survival events")
    @app_commands.describe(event_name="Select an event to get more information")
    async def event(interaction: Interaction, event_name: str):
        """Handle the event command"""
        logger.info(f"Event command called with event_name: {event_name}")

        # Show specific event info
        event_info = get_event_info(event_name.lower())
        if not event_info:
            await interaction.response.send_message(
                "❌ Event '{0}' not found. Available events: bear, foundry, crazyjoe, alliancemobilization, alliancechampionship, canyonclash, fishingtournament, frostfiremine".format(event_name),
                ephemeral=True,
            )
            return

        embed = Embed(
            title=f"{get_category_emoji(event_info['category'])} {event_info['name']}",
            description=f"Here's what you need to know about {event_info['name']}:",
            color=get_difficulty_color(event_info['difficulty']),
        )

        if 'image' in event_info:
            embed.set_thumbnail(url=event_info['image'])

        embed.add_field(name="📊 Difficulty", value=event_info.get('difficulty', 'Unknown'), inline=True)
        embed.add_field(name="⏱️ Duration", value=event_info.get('duration', 'Unknown'), inline=True)
        embed.add_field(name="🏷️ Category", value=event_info.get('category', 'Unknown'), inline=True)
        embed.add_field(name="🎁 Rewards", value=event_info.get('rewards', 'None'), inline=False)

        if event_info.get('guide'):
            embed.add_field(name="📚 Guide", value=f"[Click here]({event_info['guide']})", inline=True)
        if event_info.get('video'):
            embed.add_field(name="🎥 Video Guide", value=f"[Watch here]({event_info['video']})", inline=True)
        if event_info.get('tips'):
            embed.add_field(name="💡 Tips", value=event_info['tips'], inline=False)

        await interaction.response.send_message(embed=embed)
