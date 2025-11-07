"""/playerinfo cog - single clean implementation with logging.

This module intentionally keeps the request pattern aligned with other
working cogs: millisecond timestamp, MD5(form + SECRET), x-www-form-urlencoded
payload, and Origin header. It also logs invocation, payloads, API responses
and exceptions to the bot logger configured in `main.py` so you can inspect
`bot/log/log.txt` for issues.
"""

import re
import time
import hashlib
import aiohttp
import ssl
import asyncio
from datetime import datetime
import logging
import discord
from discord import app_commands
from discord.ext import commands
import urllib.parse

# Player API endpoint and secret (keep this in sync with your other code)
API_URL = "https://wos-giftcode-api.centurygame.com/api/player"
SECRET = "tB87#kPtkxqOS2"

# Development guild for quick command registration (replace with your guild id)
DEV_GUILD_ID = 850787279664185434
# Watermark image (user-provided). This may be a page URL; Discord requires
# an actual image URL for icon fields. We attempt to set it and will quietly
# fall back if Discord rejects it.
WATERMARK_URL = "https://cdn.discordapp.com/attachments/1435569370389807144/1436437186424606741/unnamed_4.png?ex=690f99e0&is=690e4860&hm=2262bc4ceea28787c91c5bfcb2d6e7fac28cda152c4963a9b4375eac4913b063"


def map_furnace(lv: int) -> str | None:
    """Map numeric furnace level to FC labels per user rules.

    Rules implemented:
    - 31-39 -> FC1
    - 40-44 -> FC2
    - 45-49 -> FC3
    - 50-54 -> FC4
    - 55-59 -> FC5, etc (every 5 levels after 40 increments FC index)
    """
    if lv is None:
        return None
    try:
        lv = int(lv)
    except Exception:
        return None

    if 31 <= lv <= 39:
        return "FC1"
    if lv >= 40:
        fc_index = ((lv - 40) // 5) + 2
        return f"FC{fc_index}"
    return None


class PlayerInfoCog(commands.Cog):
    """Cog that adds a /playerinfo slash command.

    The command accepts a 9-digit player id (fid) and returns a rich embed
    containing: nickname, fid, kid, furnace level (and FC mapping), small
    furnace icon and the avatar as the embed thumbnail.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('bot.playerinfo')

    @discord.app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @discord.app_commands.command(
        name="playerinfo",
        description="Get player info by 9-digit player id. Accepts comma-separated list (max 30).",
    )
    @app_commands.describe(player_id="Single 9-digit id or comma-separated list of ids (max 30)")
    async def playerinfo(self, interaction: discord.Interaction, player_id: str):
        # log invocation
        user_id = getattr(interaction.user, 'id', 'unknown')
        self.logger.info("/playerinfo invoked by user %s for player_id=%s", user_id, player_id)

        # Split comma-separated list, trim spaces, enforce limits
        ids = [p.strip() for p in str(player_id).split(',') if p.strip()]
        if not ids:
            await interaction.response.send_message("No player ids provided.", ephemeral=True)
            return
        if len(ids) > 30:
            await interaction.response.send_message("Too many ids — max 30 at a time.", ephemeral=True)
            return

        # Validate each id individually
        invalid = [p for p in ids if not re.fullmatch(r"\d{9}", p)]
        if invalid:
            await interaction.response.send_message(
                f"The following ids are invalid (must be 9 digits): {', '.join(invalid)}",
                ephemeral=True,
            )
            return

        await interaction.response.defer()  # allow time for network requests

        # prepare shared SSL/context and headers
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://wos-giftcode-api.centurygame.com",
        }

        # URL validator used by the embed builder
        def _is_valid_url(u: str) -> bool:
            if not u:
                return False
            try:
                p = urllib.parse.urlparse(u)
                return p.scheme in ("http", "https") and bool(p.netloc)
            except Exception:
                return False

        # Concurrency limiter to avoid hammering the API
        sem = asyncio.Semaphore(10)

        async def fetch_one(session: aiohttp.ClientSession, fid: str) -> tuple[str, dict | None, Exception | None]:
            """Fetch player info for a single fid. Returns (fid, json, exception).
            json is None if request/json parsing failed; exception is set on network errors.
            """
            async with sem:
                try:
                    current_time = int(time.time() * 1000)
                    form = f"fid={fid}&time={current_time}"
                    sign = hashlib.md5((form + SECRET).encode("utf-8")).hexdigest()
                    payload = f"sign={sign}&{form}"
                    self.logger.debug("playerinfo payload for %s: %s", fid, payload)
                    async with session.post(API_URL, data=payload, headers=headers, timeout=20) as resp:
                        text = await resp.text()
                        try:
                            js = await resp.json()
                        except Exception:
                            self.logger.warning("Invalid JSON response for fid=%s: %s", fid, text)
                            return fid, None, None
                        return fid, js, None
                except Exception as e:
                    self.logger.exception("Request error for fid=%s", fid)
                    return fid, None, e

        # helper to build embed from API data (or from error cases)
        def build_embed_for(fid: str, js: dict | None) -> discord.Embed:
            # default empty embed in case of network/json error
            embed = discord.Embed(colour=discord.Colour.blurple())
            if js is None:
                embed.description = "No valid response from API."
                embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]")
                return embed

            if js.get("code") != 0:
                api_msg_raw = js.get('msg') or ''
                api_msg = str(api_msg_raw).lower().replace('_', ' ')
                if ('role' in api_msg and ('not' in api_msg and ('exist' in api_msg or 'found' in api_msg))) \
                   or (('not' in api_msg) and ('exist' in api_msg or 'found' in api_msg)):
                    embed.description = "Player not found — check the 9-digit player ID and try again."
                    embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]")
                    return embed
                else:
                    embed.description = f"API error: {api_msg_raw}"
                    embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]")
                    return embed

            data = js.get('data', {})
            nickname = data.get('nickname', 'Unknown')
            kid = data.get('kid', 'N/A')
            stove_lv = data.get('stove_lv')
            stove_icon = data.get('stove_lv_content')
            avatar = data.get('avatar_image')

            # compute furnace label
            try:
                lv_int = int(stove_lv) if stove_lv is not None else None
            except Exception:
                lv_int = None
            fc = map_furnace(lv_int)

            # Build embed
            embed = discord.Embed(colour=discord.Colour.blurple())

            # Set author to nickname with stove icon if valid
            try:
                author_name = f"{nickname}"
                if stove_icon and _is_valid_url(stove_icon):
                    embed.set_author(name=author_name, icon_url=stove_icon)
                else:
                    embed.set_author(name=author_name)
            except Exception:
                embed.set_author(name=author_name)

            # Thumbnail
            if avatar and _is_valid_url(avatar):
                try:
                    embed.set_thumbnail(url=avatar)
                except Exception:
                    pass

            # Furnace display rules: only FC label when present, else numeric.
            if lv_int is None:
                furnace_display = f"```{stove_lv or 'N/A'}```"
            else:
                if fc:
                    furnace_display = f"```{fc}```"
                else:
                    furnace_display = f"```{lv_int}```"

            pid_display = f"```{fid}```"
            raw_state = str(kid or "N/A")
            if raw_state.startswith("#"):
                state_val = f"```{raw_state}```"
            else:
                state_val = f"```#{raw_state}```"

            embed.add_field(name="🪪 Player ID", value=pid_display, inline=True)
            embed.add_field(name="🏠 STATE", value=state_val, inline=True)
            embed.add_field(name="Furnace Level", value=furnace_display, inline=True)

            # Footer
            try:
                if WATERMARK_URL and _is_valid_url(WATERMARK_URL):
                    embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]", icon_url=WATERMARK_URL)
                else:
                    embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]")
            except Exception:
                embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]")

            return embed

        # perform requests reusing a single session
        results = []
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                tasks = [asyncio.create_task(fetch_one(session, fid)) for fid in ids]
                for coro in asyncio.as_completed(tasks):
                    fid, js, exc = await coro
                    if exc:
                        self.logger.warning("Network error for fid=%s: %s", fid, exc)
                        embed = discord.Embed(colour=discord.Colour.blurple(), description=f"Request error: {exc}")
                        embed.set_footer(text="Requested via /playerinfo . Magnus[ICE]")
                        await interaction.followup.send(embed=embed)
                        continue
                    # build embed from js (may be None if invalid json)
                    embed = build_embed_for(fid, js)
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            self.logger.exception("Unexpected error during batch fetch")
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(PlayerInfoCog(bot))
    # Try to sync commands to the dev guild for immediate availability
    try:
        await bot.tree.sync(guild=discord.Object(id=DEV_GUILD_ID))
        print(f"/playerinfo synced to guild {DEV_GUILD_ID}")
    except Exception as e:
        print("PlayerInfoCog: guild sync failed:", e)
