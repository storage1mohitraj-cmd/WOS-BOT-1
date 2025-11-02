# Angel Bot Deployment Guide

## For Katabump or Similar Cloud Platforms

### Required Files
- ✅ `app.py` - Main bot file
- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - Process configuration
- ✅ `runtime.txt` - Python version
- ✅ `.env` - Environment variables (don't upload, set in platform settings)

### Environment Variables Required
Make sure to set these in your Katabump dashboard:

**Required:**
```
DISCORD_TOKEN=your_discord_bot_token
OPENROUTER_API_KEY_1=your_openrouter_key_1
```

**Optional (but recommended):**
```
GUILD_ID_1=your_first_guild_id
GUILD_ID_2=your_second_guild_id
OPENROUTER_API_KEY_2=your_openrouter_key_2
OPENROUTER_API_KEY_3=your_openrouter_key_3
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
```

### Deployment Steps

1. **Upload Files**: Upload all Python files and the requirements.txt
2. **Set Environment Variables**: Add all the environment variables in your platform's settings
3. **Install Dependencies**: The platform should automatically install from requirements.txt
4. **Start Process**: Use the worker process (defined in Procfile)

### Troubleshooting

**"TypeError: int() argument must be a string... not 'NoneType'"**:
- ✅ **FIXED** - This error has been resolved in the updated code
- The bot now handles missing GUILD_ID_1/GUILD_ID_2 gracefully
- You only need to set DISCORD_TOKEN and OPENROUTER_API_KEY_1 as required variables

**"Module discord not found"**:
- Make sure `requirements.txt` is in the root directory
- Verify all environment variables are set
- Check if the platform successfully installed dependencies

**"No module named 'api_manager'"**:
- Make sure all your Python files are uploaded
- Check file names match exactly (case-sensitive)

**Bot starts but commands don't work**:
- If no GUILD_ID_1/GUILD_ID_2 are set, commands sync globally (takes 1 hour)
- Set at least GUILD_ID_1 for instant command updates in your server
- Get Guild ID by right-clicking your server name → Copy Server ID

### Alternative Requirements (if needed)
If you encounter issues, try this minimal requirements.txt:

```
discord.py>=2.3.0
aiohttp>=3.8.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
asyncio
```
