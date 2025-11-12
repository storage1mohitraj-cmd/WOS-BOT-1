# Fix Render Data Loss - Use MongoDB Persistence

## Problem
Every time you restart the bot on Render, alliance data and player IDs are lost because:
- Local SQLite files are stored in ephemeral container storage
- Container filesystem is deleted on restart/redeploy
- MongoDB is the only persistent storage option on Render

## Solution: Configure MongoDB for Persistence

### Step 1: Verify MongoDB Connection
You already have MongoDB set up (`mongo_uri.txt` exists). Environment variable should be:

```bash
# In Render Environment Variables add:
MONGO_DB_URI=mongodb+srv://iammagnusx1_db_user:zYFHUOjjXhfGLpMs@reminder.hlx5aem.mongodb.net/?appName=REMINDER
```

### Step 2: Update app.py to Use MongoDB for Alliance Data

The bot currently tries to use local SQLite. Force it to use MongoDB:

**In app.py, modify `ensure_db_tables()` function to skip SQLite creation when MongoDB is available:**

```python
def ensure_db_tables():
    """Create SQLite tables only if MongoDB is NOT available"""
    # If MongoDB is available, skip SQLite setup entirely
    if mongo_enabled():
        logger.info("[DB] MongoDB is enabled - skipping SQLite table creation")
        return
    
    # Only create SQLite tables if MongoDB is unavailable
    db_dir = os.path.join(os.path.dirname(__file__), 'db')
    # ... rest of SQLite setup
```

### Step 3: Verify MongoDB Adapters are Loaded

Check that these cogs load the MongoDB adapters:
- `cogs/alliance.py` - should use MongoDB for alliance data
- `cogs/gift_operations.py` - should use MongoDB for gift codes
- `reminder_system.py` - should use MongoDB for reminders

### Step 4: Migrate Existing Data (Optional but Recommended)

If you have existing alliance data locally, migrate it to MongoDB:

```bash
cd "f:/STARK-whiteout survival bot/DISCORD BOT"
python db_migration_tool.py
```

This will:
1. Backup all SQLite databases
2. Export alliance member data
3. Show you what will be migrated

### Step 5: Configure Render Environment Variables

In Render dashboard for your bot service:

1. Go to **Environment**
2. Add these variables:
```
MONGO_DB_URI=mongodb+srv://iammagnusx1_db_user:zYFHUOjjXhfGLpMs@reminder.hlx5aem.mongodb.net/?appName=REMINDER
```

3. Redeploy the bot

### Step 6: Verify MongoDB is Working

When bot starts, check logs for:
```
[DB] MongoDB is enabled - using Mongo adapters
```

If you see this, MongoDB is active and data will persist!

## Why This Works

- **MongoDB**: Cloud-hosted database, data persists across restarts ✅
- **SQLite files**: Stored in container, deleted on restart ❌

## Testing Persistence

1. Add alliance member with player ID
2. Restart bot on Render
3. Check if alliance member is still there
4. Member should persist! ✅

## Troubleshooting

**If data still lost after restart:**
- Check Render logs: `MongoDB is enabled` message?
- Verify `MONGO_DB_URI` env variable is set in Render
- Check MongoDB database in MongoDB Atlas console
- Ensure cogs are using `mongo_adapters.py`

**If MongoDB connection fails:**
- Test connection string locally first
- Verify network access from Render IP
- Check MongoDB Atlas firewall settings (allow all IPs)
