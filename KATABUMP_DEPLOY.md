# 🚀 Deploy Angel Bot to Katabump

## ✅ FIXED: All Errors Resolved

✅ **"At least one valid API key is required"** - Fixed with improved environment loading
✅ **"ModuleNotFoundError: No module named 'user_mapping'"** - Fixed with optional import and simplified file

## 📁 Files to Upload to Katabump

Upload ALL these files to your Katabump project:

### Core Files
- ✅ `app.py` (main bot - **UPDATED with fixes**)
- ✅ `requirements.txt` (dependencies)
- ✅ `Procfile` (worker: python app.py)
- ✅ `runtime.txt` (python-3.11.0)
- ✅ **`.env`** (contains your tokens - **IMPORTANT!**)

### Supporting Files
- ✅ `api_manager.py`
- ✅ `event_tips.py`
- ✅ `angel_personality.py`
- ✅ `user_mapping.py`
- ✅ `gift_codes.py`
- ✅ All other `.py` files in your folder

## 🔐 Your .env File Contents

Make sure your `.env` file contains exactly this:

```env
# DISCORD BOT CONFIGURATION
DISCORD_TOKEN=

# DISCORD GUILD IDS (SERVER IDS)
GUILD_ID_1=
GUILD_ID_2=

# OPENROUTER API KEYS
OPENROUTER_API_KEY_1=
OPENROUTER_API_KEY_2=
OPENROUTER_API_KEY_3=
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free
```

## 🎯 Deployment Steps

1. **Upload all files** including the `.env` file
2. **Set process type to `worker`** (not web)
3. **Start the bot**
4. **Check logs** - should see:
   ```
   ✅ Loaded environment from: /home/container/.env
   🔑 API Key debug info:
      - API Key 1: Found (length: 73)
      - API Key 2: Found (length: 73)
      - API Key 3: Found (length: 73)
   🔑 Total valid API keys: 3
   🚀 Starting Whiteout Survival Alliance Bot...
   ```

## 🔍 Expected Success Output

```
✅ Loaded environment from: [path]
🔑 Total valid API keys: 3
Initialized OpenRouter manager with 3 API keys
🚀 Starting Whiteout Survival Alliance Bot...
✅ Discord token: Set
✅ OpenRouter keys: 3 configured
📍 Guild IDs: Primary: 8, Secondary: 
Angel#7177 has connected to Discord!
```

## ❌ If You Still Get Errors

**"At least one valid API key is required":**
- ✅ This is now fixed with better environment loading
- Make sure `.env` file is uploaded
- Check Katabump logs for "Loaded environment from:" message

**"Module not found":**
- Make sure all `.py` files are uploaded
- Check `requirements.txt` is present

## 🎉 Bot Commands

Once running, your bot will have these slash commands:
- `/ask` - Ask Angel anything
- `/event` - Get Whiteout Survival event info
- `/giftcode` - Get active gift codes
- `/profile` - View/manage user profile

The bot should now start successfully on Katabump! 🚀
