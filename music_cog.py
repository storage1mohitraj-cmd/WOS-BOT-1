import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import asyncio
import re
import logging
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}  # Guild ID: List of tracks
        self.now_playing = {}  # Guild ID: current track
        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to Lavalink nodes when the bot is ready."""
        await self.bot.wait_until_ready()

        try:
            # Initialize Spotify client
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
            ))

            # Connect to Lavalink
            client = wavelink.Client(bot=self.bot)
            await client.connect(nodes=[{
                'host': os.getenv('LAVALINK_HOST', '127.0.0.1'),
                'port': int(os.getenv('LAVALINK_PORT', 2334)),
                'password': os.getenv('LAVALINK_PASSWORD', 'youshallnotpass'),
                'region': 'na'
            }])
            logger.info("Connected to Lavalink node successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Lavalink node: {e}")

    def _create_progress_bar(self, current, total, length=15):
        """Create a text progress bar."""
        filled = int((current / total) * length)
        bar = "▬" * filled + "🔘" + "▬" * (length - filled - 1)
        return bar

    async def _ensure_voice(self, interaction):
        """Ensure the bot and user are in a voice channel."""
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            return None, "You need to be in a voice channel first!"

        channel = member.voice.channel
        logger.info(f"User is in voice channel: {channel.name}")
        
        try:
            if not interaction.guild.voice_client:
                try:
                    player = await channel.connect(cls=wavelink.Player)
                    await player.set_volume(100)
                except Exception as e:
                    logger.error(f"Error connecting to channel: {e}")
                    return None, f"Error connecting to channel: {str(e)}"
            else:
                player = interaction.guild.voice_client
            
            if player.channel != channel:
                return None, "You need to be in the same voice channel as the bot!"
                
            await interaction.guild.change_voice_state(channel=channel, self_deaf=True)
            return player, None
            
        except Exception as e:
            logger.error(f"Error during voice connection: {e}")
            return None, f"Error connecting to voice channel: {str(e)}"

    async def _send_now_playing_embed(self, guild, track):
        """Send an embed with the currently playing track."""
        try:
            embed = discord.Embed(color=discord.Color.blue())
            
            embed.title = "🎵 Now Playing"
            embed.description = f"[{track.title}]({track.uri})"
            
            # Get track info
            duration = track.duration
            current_position = 0
            if guild.voice_client:
                current_position = guild.voice_client.position

            # Format timestamps
            duration_str = str(timedelta(milliseconds=int(duration))) if duration else "Unknown"
            position_str = str(timedelta(milliseconds=int(current_position))) if current_position else "0:00"
            
            # Create progress bar
            if duration:
                progress_bar = self._create_progress_bar(current_position or 0, duration)
                embed.add_field(
                    name="Progress",
                    value=f"{position_str} {progress_bar} {duration_str}",
                    inline=False
                )
            
            # Add author/artist
            if hasattr(track, 'author'):
                embed.add_field(name="Artist", value=track.author, inline=True)
            
            # Add thumbnail if available
            if hasattr(track, 'thumb'):
                embed.set_thumbnail(url=track.thumb)
                
            # Add playback controls guide
            controls = (
                "**Controls:**\n"
                "⏸️ `/pause` - Pause\n"
                "▶️ `/resume` - Resume\n"
                "⏭️ `/skip` - Skip\n"
                "⏹️ `/stop` - Stop\n"
                "🔊 Volume at 100%"
            )
            embed.add_field(name="Controls", value=controls, inline=False)
            
            # Add queue info if available
            if guild.id in self.song_queue and self.song_queue[guild.id]:
                next_up = self.song_queue[guild.id][0]
                queue_length = len(self.song_queue[guild.id])
                queue_info = f"Next up: **{next_up.title}**\n{queue_length} total in queue"
                embed.add_field(name="Queue", value=queue_info, inline=False)

            # Try to find a suitable channel to send the embed
            channel = discord.utils.get(guild.text_channels, name="music")
            if not channel:
                channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
            
            if channel:
                await channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error creating now playing embed: {e}")
            # Send a simplified embed as fallback
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"{track.title}",
                color=discord.Color.blue()
            )
            if channel:
                await channel.send(embed=embed)

    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play a song from YouTube or Spotify"""
        await interaction.response.defer()
        
        logger.info(f"Play command received from {interaction.user.name}, query: {query}")
        
        # Debug voice state
        member = interaction.guild.get_member(interaction.user.id)
        if member and member.voice:
            logger.info(f"User is in voice channel: {member.voice.channel.name}")
        else:
            logger.info("User is not in a voice channel")
            
        player, error_message = await self._ensure_voice(interaction)
        if error_message:
            logger.info(f"Voice connection error: {error_message}")
            await interaction.followup.send(error_message, ephemeral=True)
            return
        if not player:
            logger.info("No player returned from _ensure_voice")
            return

        try:
            # Handle Spotify URLs
            spotify_pattern = r'https://open\.spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)'
            if match := re.match(spotify_pattern, query):
                type_, id_ = match.groups()
                try:
                    if type_ == 'track':
                        spotify_track = self.sp.track(id_)
                        search_query = f"{spotify_track['name']} - {spotify_track['artists'][0]['name']}"
                        tracks = await wavelink.YouTubeTrack.search(search_query)
                        if not tracks:
                            await interaction.followup.send("Could not find the track!", ephemeral=True)
                            return
                        track = tracks[0]
                    
                    elif type_ in ['playlist', 'album']:
                        if type_ == 'playlist':
                            results = self.sp.playlist_tracks(id_)
                        else:
                            results = self.sp.album_tracks(id_)
                        
                        tracks = []
                        for item in results['items'][:50]:
                            track_info = item['track'] if type_ == 'playlist' else item
                            search_query = f"{track_info['name']} - {track_info['artists'][0]['name']}"
                            results = await wavelink.YouTubeTrack.search(search_query)
                            if results:
                                tracks.append(results[0])
                        
                        if not tracks:
                            await interaction.followup.send("Could not find any tracks!", ephemeral=True)
                            return
                        
                        if not player.is_playing():
                            first_track = tracks.pop(0)
                            await player.play(first_track)
                            await self._send_now_playing_embed(interaction.guild, first_track)
                            self.now_playing[interaction.guild_id] = first_track
                        
                        self.song_queue.setdefault(interaction.guild_id, []).extend(tracks)
                        await interaction.followup.send(f"Added {len(tracks)} tracks to the queue!")
                        return
                        
                except Exception as e:
                    logger.error(f"Error processing Spotify URL: {e}")
                    await interaction.followup.send("Error processing Spotify URL!", ephemeral=True)
                    return
            else:
                # Regular YouTube/URL search
                tracks = await wavelink.YouTubeTrack.search(query)
                if not tracks:
                    await interaction.followup.send("Could not find any tracks!", ephemeral=True)
                    return
                track = tracks[0]

            # Play the track or add it to the queue
            if not player.is_playing():
                await player.play(track)
                self.now_playing[interaction.guild_id] = track
                await self._send_now_playing_embed(interaction.guild, track)
                await interaction.followup.send("🎵 Now playing!", ephemeral=True)
            else:
                self.song_queue.setdefault(interaction.guild_id, []).append(track)
                await interaction.followup.send(
                    f"Added **{track.title}** to the queue!\n" +
                    f"Position in queue: {len(self.song_queue[interaction.guild_id])}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in play command: {e}")
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="pause")
    async def pause(self, interaction: discord.Interaction):
        """Pause the current song"""
        player, error_message = await self._ensure_voice(interaction)
        if error_message:
            await interaction.response.send_message(error_message, ephemeral=True)
            return
        if not player:
            return

        if player.is_playing():
            await player.pause()
            await interaction.response.send_message("⏸️ Paused the music!", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing right now!", ephemeral=True)

    @app_commands.command(name="resume")
    async def resume(self, interaction: discord.Interaction):
        """Resume the current song"""
        player, error_message = await self._ensure_voice(interaction)
        if error_message:
            await interaction.response.send_message(error_message, ephemeral=True)
            return
        if not player:
            return

        if player.is_paused():
            await player.resume()
            await interaction.response.send_message("▶️ Resumed the music!", ephemeral=True)
        else:
            await interaction.response.send_message("The music is not paused!", ephemeral=True)

    @app_commands.command(name="skip")
    async def skip(self, interaction: discord.Interaction):
        """Skip the current song"""
        player, error_message = await self._ensure_voice(interaction)
        if error_message:
            await interaction.response.send_message(error_message, ephemeral=True)
            return
        if not player:
            return

        if player.is_playing():
            await player.stop()
            await interaction.response.send_message("⏭️ Skipped the current song!", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing right now!", ephemeral=True)

    @app_commands.command(name="stop")
    async def stop(self, interaction: discord.Interaction):
        """Stop playing and clear the queue"""
        player, error_message = await self._ensure_voice(interaction)
        if error_message:
            await interaction.response.send_message(error_message, ephemeral=True)
            return
        if not player:
            return

        if player.is_playing():
            self.song_queue[interaction.guild_id] = []
            await player.stop()
            await interaction.response.send_message("⏹️ Stopped the music and cleared the queue!", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing right now!", ephemeral=True)

    @app_commands.command(name="queue")
    async def queue(self, interaction: discord.Interaction):
        """Show the current music queue"""
        if interaction.guild_id not in self.song_queue or not self.song_queue[interaction.guild_id]:
            await interaction.response.send_message("The queue is empty!", ephemeral=True)
            return

        queue = self.song_queue[interaction.guild_id]
        embed = discord.Embed(title="🎵 Music Queue", color=discord.Color.blue())
        
        if interaction.guild_id in self.now_playing:
            current = self.now_playing[interaction.guild_id]
            embed.add_field(
                name="Now Playing",
                value=f"[{current.title}]({current.uri})",
                inline=False
            )

        queue_text = "\n".join(
            f"{i+1}. [{track.title}]({track.uri})" 
            for i, track in enumerate(queue[:10])
        )
        
        if queue_text:
            embed.add_field(
                name="Up Next",
                value=queue_text + (f"\n... and {len(queue) - 10} more" if len(queue) > 10 else ""),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave")
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)
            return

        await interaction.guild.voice_client.disconnect()
        self.song_queue[interaction.guild_id] = []
        self.now_playing.pop(interaction.guild_id, None)
        await interaction.response.send_message("👋 Left the voice channel!", ephemeral=True)

    async def cog_unload(self):
        """Clean up when the cog is unloaded."""
        try:
            for guild in self.bot.guilds:
                if guild.voice_client:
                    await guild.voice_client.disconnect()
            
            self.song_queue.clear()
            self.now_playing.clear()
            
            await wavelink.Client.destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player, track, reason):
        """Called when a track ends. Will play the next song in queue if it exists."""
        guild_id = player.guild.id
        
        try:
            if guild_id in self.song_queue and self.song_queue[guild_id]:
                next_track = self.song_queue[guild_id].pop(0)
                await player.play(next_track)
                self.now_playing[guild_id] = next_track
                await self._send_now_playing_embed(player.guild, next_track)
        except Exception as e:
            logger.error(f"Error in track end event: {e}")

async def setup(bot):
    await bot.add_cog(Music(bot))