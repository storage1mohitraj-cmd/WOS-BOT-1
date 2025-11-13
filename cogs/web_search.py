import asyncio
import discord
from discord.ext import commands
from discord import app_commands

try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None


class WebSearch(commands.Cog):
    """Simple web search cog using duckduckgo-search.

    Provides a slash command `/search` that returns the top search results.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="search", description="Search the web and return top results")
    @app_commands.describe(query="Search query", max_results="Number of results (1-5)")
    async def search(self, interaction: discord.Interaction, query: str, max_results: int = 3):
        if DDGS is None:
            await interaction.response.send_message(
                "The search integration is not available. Please install `duckduckgo-search`.",
                ephemeral=True,
            )
            return

        max_results = max(1, min(5, max_results))

        await interaction.response.defer()
        loop = asyncio.get_event_loop()

        try:
            # DDGS is synchronous/blocking; run in executor
            def _sync_search(q, mx):
                try:
                    with DDGS() as ddgs:
                        return ddgs.text(q, max_results=mx)
                except Exception:
                    return []

            results = await loop.run_in_executor(None, lambda: _sync_search(query, max_results))

            if not results:
                await interaction.followup.send("No results found.", ephemeral=True)
                return

            parts = []
            for r in results[:max_results]:
                title = r.get("title") or r.get("text") or "(no title)"
                href = r.get("href") or r.get("url") or r.get("link") or ""
                snippet = r.get("body") or r.get("snippet") or ""

                # Build a compact block for each result
                block = f"**{title}**\n{snippet}\n<{href}>"
                parts.append(block)

            content = "\n\n".join(parts)

            if len(content) > 1900:
                content = content[:1900] + "\n\n...[truncated]"

            await interaction.followup.send(content)

        except Exception as e:
            await interaction.followup.send(f"Search failed: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WebSearch(bot))
