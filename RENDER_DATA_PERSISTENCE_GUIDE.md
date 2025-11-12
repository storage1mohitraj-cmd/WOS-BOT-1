# How to Fix Data Loss on Render - Step by Step

## The Problem

Your bot loses all alliance data and player IDs when it restarts on Render because:
- **Render uses ephemeral (temporary) storage**
- Files written to the container filesystem are **deleted on every restart**
- Local SQLite databases are **not persistent**

## The Solution: Use MongoDB (Persistent Cloud Database)

You already have MongoDB configured! Just need to enable it in Render.

---

## Step-by-Step Fix

### Step 1: Add MongoDB Environment Variable to Render

1. Go to your **Render Dashboard**
2. Select your **Discord Bot Service**
3. Click **Environment** (or Environment tab)
4. Add this environment variable:

```
MONGO_URI=mongodb+srv://iammagnusx1_db_user:zYFHUOjjXhfGLpMs@reminder.hlx5aem.mongodb.net/?appName=REMINDER
```

5. Also add (optional but recommended):
```
MONGO_DB_NAME=discord_bot
```

6. Click **Save Changes**
7. Render will **automatically redeploy** your bot

### Step 2: Verify MongoDB is Enabled

After the bot redeploys:
- Check **Render Logs**
- Look for message: `MongoDB is enabled` or `Mongo adapters loaded`
- If you see it, MongoDB is working! ✅

### Step 3: Test Persistence

1. Add an alliance member via bot command
2. Note the player ID
3. **Restart the bot** in Render dashboard
4. Check if the player is still there
5. Player should persist! ✅

---

## What Happens Behind the Scenes

**Before (SQLite - Lost Data):**
```
Bot Restart
  ↓
Container killed
  ↓
Local SQLite files deleted ❌
  ↓
All data gone!
```

**After (MongoDB - Data Saved):**
```
Bot Restart
  ↓
Container killed
  ↓
SQLite files deleted (doesn't matter!)
  ↓
Bot reconnects to MongoDB cloud ✅
  ↓
All data restored from MongoDB! ✅
```

---

## Common Issues & Solutions

### Issue 1: "MONGO_URI not set"
**Solution:** 
- Verify you added the environment variable in Render
- Check spelling: `MONGO_URI` (not `MONGO_DB_URI`)
- Redeploy the bot

### Issue 2: MongoDB Connection Refused
**Solution:**
- Verify connection string is correct (copy from your mongo_uri.txt)
- Check MongoDB Atlas firewall settings
- Allow "0.0.0.0/0" (all IPs) if needed for Render

### Issue 3: Still Losing Data After Restart
**Solution:**
- Check bot logs to confirm `mongo_enabled()` returns True
- Verify data is actually being written to MongoDB (check MongoDB Atlas)
- Make sure all cogs are using `mongo_adapters.py`

---

## Files Involved

These files now use MongoDB (if `MONGO_URI` is set):
- `reminder_system.py` - stores reminders
- `db/mongo_adapters.py` - handles MongoDB connections
- `cogs/alliance.py` - stores alliance data
- `cogs/gift_operations.py` - stores gift codes
- App automatically falls back to SQLite if MongoDB unavailable

---

## Permanent Fix Commands

If you want to migrate all existing local data to MongoDB:

```bash
# Backup existing databases
python db_migration_tool.py

# This will show you what data exists locally
# and prepare it for MongoDB migration
```

---

## Summary

✅ **Required Action:**
1. Add `MONGO_URI` environment variable in Render
2. Redeploy bot
3. Data will now persist across restarts!

✅ **Why This Works:**
- MongoDB is hosted on Atlascloud (persistent)
- Render can access it across restarts
- Local files are ephemeral (discarded on restart)

**Your data is safe once MongoDB is configured!** 🎉
