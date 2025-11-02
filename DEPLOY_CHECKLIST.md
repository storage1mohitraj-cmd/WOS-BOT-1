# 🚀 Katabump Deployment Checklist

## ✅ Quick Setup (Fixed the TypeError!)

### 1. **Upload Files**
Upload these files to your Katabump project:
- [x] `app.py` (main bot - **UPDATED with error fixes**)
- [x] `requirements.txt` (dependencies)
- [x] `Procfile` (tells Katabump how to run)
- [x] `runtime.txt` (Python version)
- [x] All other `.py` files (`api_manager.py`, `event_tips.py`, etc.)

### 2. **Set Environment Variables** (in Katabump Dashboard)
**REQUIRED - Bot won't start without these:**
```
DISCORD_TOKEN=your_actual_bot_token
OPENROUTER_API_KEY_1=your_actual_api_key
```

**OPTIONAL - For faster command updates:**
```
GUILD_ID_1=your_server_id_here
```

### 3. **Deploy & Start**
- Set process type to: **`worker`** (not web)
- Start the bot
- Check logs for: "🚀 Starting Whiteout Survival Alliance Bot..."

## 🎯 Fixed Issues

- ✅ **TypeError with GUILD_ID_1** - Now handles missing environment variables
- ✅ **Better error messages** - Shows exactly what's missing
- ✅ **Graceful fallbacks** - Works without guild IDs (slower command sync)
- ✅ **Cleaner requirements.txt** - Only essential packages

## 🔍 Expected Log Output

**Success:**
```
✅ Discord token: Set
✅ OpenRouter keys: 1 configured
📍 Guild IDs: Primary: 1234567890
🚀 Starting Whiteout Survival Alliance Bot...
```

**If missing environment variables:**
```
❌ Missing required environment variables:
   - DISCORD_TOKEN
📝 Please set these environment variables in your Katabump dashboard:
   DISCORD_TOKEN=your_bot_token
   OPENROUTER_API_KEY_1=your_api_key
```

## 🆘 Still Having Issues?

1. **Check Katabump logs** for specific error messages
2. **Verify environment variables** are actually set in dashboard
3. **Make sure** all Python files are uploaded
4. **Process type** should be `worker`, not `web`

The bot should now start successfully with just DISCORD_TOKEN and OPENROUTER_API_KEY_1! 🎉
