import discord
from discord.ext import commands
import re
import sqlite3
import logging

logger = logging.getLogger(__name__)

class PlayerIDValidator(commands.Cog):
    """Cog to validate player IDs in messages and react with emojis"""
    
    def __init__(self, bot):
        self.bot = bot
        self.conn_users = sqlite3.connect('db/users.sqlite')
        self.c_users = self.conn_users.cursor()
        
    def _check_player_id_exists(self, player_id: str) -> bool:
        """Check if a player ID exists in the database"""
        try:
            self.c_users.execute("SELECT fid FROM users WHERE fid = ?", (player_id,))
            result = self.c_users.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking player ID {player_id}: {e}")
            return False
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages containing 9-digit player IDs"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Find all 9-digit numbers in the message
        # Pattern: exactly 9 consecutive digits
        pattern = r'\b\d{9}\b'
        matches = re.findall(pattern, message.content)
        
        if not matches:
            return
        
        # Check each 9-digit number found
        for player_id in matches:
            try:
                # Check if the player ID exists in the database
                if self._check_player_id_exists(player_id):
                    # Valid player ID - react with ✅
                    await message.add_reaction('✅')
                    logger.info(f"Valid player ID detected: {player_id} in message {message.id}")
                else:
                    # Invalid player ID - react with ❌
                    await message.add_reaction('❌')
                    logger.info(f"Invalid player ID detected: {player_id} in message {message.id}")
                
                # Only react once per message (for the first 9-digit number found)
                break
                
            except discord.Forbidden:
                logger.warning(f"Missing permissions to add reaction in channel {message.channel.id}")
                break
            except discord.HTTPException as e:
                logger.error(f"Failed to add reaction: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing player ID {player_id}: {e}")
                break

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(PlayerIDValidator(bot))
