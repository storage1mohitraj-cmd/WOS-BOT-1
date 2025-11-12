# Fix Data Loss Issue - MongoDB Only (No SQLite)

## Problem Identified

**Why data was lost after restart:**
1. Alliance cog was **hardcoded to use SQLite** instead of checking for MongoDB
2. SQLite files are stored in **ephemeral container storage** on Render
3. Container restarts **delete all ephemeral files**
4. Data appeared for a few minutes because SQLite was being read locally
5. Then disappeared when container restarted

## Solution Implemented

✅ **Updated bot to prioritize MongoDB:**
1. Modified `ensure_db_tables()` to skip SQLite if `MONGO_URI` is set
2. Added `AllianceMembersAdapter` for storing alliance data in MongoDB
3. Created `alliance_db_wrapper.py` to seamlessly use MongoDB/SQLite
4. Bot now logs which database is being used at startup

## What You Need To Do

### Step 1: Set MongoDB Environment Variable in Render

**This is CRITICAL - without it, data will continue to be lost!**

1. Go to **Render Dashboard** → Your Discord Bot Service
2. Click **Environment** or **Settings → Environment**
3. Add this variable:
   ```
   MONGO_URI=mongodb+srv://iammagnusx1_db_user:zYFHUOjjXhfGLpMs@reminder.hlx5aem.mongodb.net/?appName=REMINDER
   ```
4. Click **Save** (Render auto-redeploys)

### Step 2: Verify MongoDB is Active

After restart, check the bot logs for:

```
[DB] ✅ MONGO_URI detected - Using MongoDB for ALL data persistence
[Alliance DB] ✅ Using MongoDB for persistent storage
```

**If you see these messages → MongoDB is working! ✅**

If you see:
```
⚠️  MONGO_URI not set - Falling back to SQLite
```

→ MongoDB is NOT set up, data will be lost! ❌

### Step 3: Test Persistence

1. Add an alliance member via bot
2. Note the **player ID**
3. **Restart the bot** from Render dashboard
4. Check if the member still exists
5. Member should be there! ✅

## Database Wrapper System

The bot now uses `alliance_db_wrapper.py` which:

```
Alliance Cog
    ↓
AllianceDatabase (wrapper)
    ↓
    ├─→ If MONGO_URI set → MongoDB ✅ (Persistent)
    └─→ If MONGO_URI NOT set → SQLite ⚠️ (Ephemeral)
```

**Flow on Render:**
```
MONGO_URI set?
    YES → MongoDB (data persists) ✅
    NO → SQLite (data deleted on restart) ❌
```

## Code Changes Made

### 1. Modified `app.py`
- `ensure_db_tables()` now checks for `MONGO_URI`
- Skips SQLite creation if MongoDB is available
- Logs which database backend is in use

### 2. Enhanced `db/mongo_adapters.py`
- Added `AllianceMembersAdapter` class
- Methods: `upsert_member()`, `get_member()`, `get_all_members()`, `delete_member()`, `clear_all()`
- All data saved with `created_at` and `updated_at` timestamps

### 3. Created `db/alliance_db_wrapper.py`
- Transparent wrapper for alliance data
- Auto-detects MongoDB availability
- Falls back to SQLite gracefully
- Logs all operations with clear messages

## What Data is Now Persistent

✅ Alliance members and player IDs
✅ Player stats (levels, furnace, stove, etc.)
✅ Gift codes and redemptions
✅ User reminders
✅ Birthday entries

## Troubleshooting

### Data still disappears after restart
**Check:**
1. Is `MONGO_URI` set in Render? (check Settings → Environment)
2. Is MongoDB connection working? (check bot logs at startup)
3. Verify data exists in MongoDB Atlas dashboard

### MongoDB connection error
**Solution:**
1. Verify connection string is correct
2. Check MongoDB Atlas firewall (allow 0.0.0.0/0)
3. Ensure network is stable

### SQLite still being used
**Check logs:**
```
[Alliance DB] ✅ Using MongoDB for persistent storage
```

If missing, MongoDB is not configured!

## Summary

✅ **Before:** Data lost every restart (SQLite ephemeral storage)
✅ **After:** Data persists (MongoDB cloud storage)

**All you need to do:**
1. Add `MONGO_URI` environment variable in Render
2. Verify "MongoDB is enabled" in logs
3. Data will persist from now on!

**The bot will now automatically:**
- Use MongoDB for Render (persistent) ✅
- Use SQLite for local development (temporary) ⚠️
- Log which backend is active at startup
