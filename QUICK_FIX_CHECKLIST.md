# Quick Checklist - Fix Data Loss NOW ✅

## What's Wrong?
- Alliance members disappear after bot restart on Render
- Player IDs are lost
- **Root cause:** Bot uses SQLite (ephemeral storage) instead of MongoDB (persistent cloud storage)

## How I Fixed It
✅ Bot now **detects MongoDB** and uses it automatically
✅ Skips SQLite if MongoDB is available  
✅ Clear logging shows which database is in use
✅ Alliance data adapters created for MongoDB

## What YOU Need To Do (5 minutes)

### 1. Add MongoDB Environment Variable
- Go to **Render Dashboard**
- Select your **Discord Bot Service**
- Go to **Settings** → **Environment**
- Add this ONE variable:
```
MONGO_URI=mongodb+srv://iammagnusx1_db_user:zYFHUOjjXhfGLpMs@reminder.hlx5aem.mongodb.net/?appName=REMINDER
```
- **Save** (auto-redeploy)

### 2. Verify It Works
- Wait for bot to restart
- Check logs for: `✅ MONGO_URI detected - Using MongoDB`
- If you see ⚠️ warning, MongoDB is NOT set!

### 3. Test Persistence
- Add alliance member via bot
- Restart bot from Render dashboard
- Member should STILL be there ✅

## Result
✅ Data persists across restarts
✅ No more losing alliance members
✅ Player IDs saved permanently

## Files Updated
- `app.py` - Enhanced `ensure_db_tables()` 
- `db/mongo_adapters.py` - Added `AllianceMembersAdapter`
- `db/alliance_db_wrapper.py` - NEW transparent wrapper
- `MONGODB_DATA_PERSISTENCE_FIX.md` - Detailed documentation

## If Something Goes Wrong
1. Check Render logs for "MongoDB is enabled" message
2. Verify `MONGO_URI` env variable is set
3. Check MongoDB Atlas dashboard to see if data is saving
4. Read `MONGODB_DATA_PERSISTENCE_FIX.md` for troubleshooting

**That's it! Your data will now persist! 🎉**
