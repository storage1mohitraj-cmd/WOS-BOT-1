# 🗄️ PERSISTENT DATA STORAGE SOLUTION

## The Problem

**Your bot works locally but data is empty on Render because:**

1. ❌ **SQLite is file-based** - Files stored on your computer
2. ❌ **Render has ephemeral storage** - Container deleted when bot restarts
3. ❌ **No data persists** - Fresh databases created each time

This is why:
- ✅ **Local:** Player data saved in `db/alliance.sqlite`
- ❌ **Render:** Empty database (lost when container restarts)

---

## ✅ SOLUTION: Use MongoDB

Your bot already supports MongoDB! You just need to configure it.

### Step 1: Get MongoDB URI

**Option A: MongoDB Atlas (Cloud - Recommended)**
1. Go to https://mongodb.com/cloud/atlas
2. Create free account
3. Create cluster
4. Get connection string:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/botname?retryWrites=true&w=majority
   ```

**Option B: Local MongoDB**
```
mongodb://localhost:27017/botname
```

### Step 2: Migrate Your Data

Run the migration tool to backup and export your data:

```powershell
python db_migration_tool.py
```

This creates:
- ✅ Backup of all SQLite databases
- ✅ Export of alliance member data
- ✅ Migration script (`migrate_to_mongo.py`)

### Step 3: Upload to MongoDB

```powershell
python migrate_to_mongo.py "mongodb+srv://user:password@cluster.mongodb.net/botname"
```

This will:
- ✅ Upload all alliance members
- ✅ Upload all gift codes
- ✅ Upload all settings
- ✅ Verify data is there

### Step 4: Configure Render

Add environment variable on Render:
```
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/botname
```

### Step 5: Bot Uses MongoDB

Your bot already has MongoDB support! Once `MONGO_URI` is set:
- ✅ Data persists across restarts
- ✅ Data survives container updates
- ✅ Shared across multiple bot instances

---

## 📊 Data Flow Comparison

### Before (Broken)
```
Local Bot → SQLite ✓
                ↓
    Render Bot → Empty SQLite ✗
```

### After (Fixed)
```
Local Bot → SQLite ✓
    ↓
MongoDB Atlas (Cloud)
    ↓
Render Bot → MongoDB ✓
```

---

## 🚀 Quick Start (TL;DR)

1. **Backup data:**
   ```powershell
   python db_migration_tool.py
   ```

2. **Get MongoDB URI** from Atlas or local install

3. **Upload your data:**
   ```powershell
   python migrate_to_mongo.py "YOUR_MONGO_URI_HERE"
   ```

4. **Add to Render environment:**
   ```
   MONGO_URI=YOUR_MONGO_URI_HERE
   ```

5. **Deploy!** Data persists now ✅

---

## ✅ Verification

After deployment, check that your data is there:

1. Deploy bot to Render
2. Bot should load existing data
3. Run `/alliance info` or similar command
4. Should see your saved data ✓

---

## 🛡️ Data Safety

- ✅ **Backups created** - All data backed up locally
- ✅ **MongoDB is persistent** - Data survives forever
- ✅ **No data loss** - Original SQLite files untouched
- ✅ **Redundant** - Can fallback to SQLite if needed

---

## 📝 What Gets Migrated

| Data | Source | Destination |
|------|--------|-------------|
| Alliance Members | `users.sqlite` | `alliance_members` collection |
| Gift Codes | `giftcode.sqlite` | `gift_codes` collection |
| Settings | `settings.sqlite` | `settings` collection |
| Player IDs | `users.sqlite` | `alliance_members` collection |

---

## 🔗 Environment Variables

### Local Development
```bash
# Optional - leave empty to use SQLite
# MONGO_URI=
```

### Render Production
```bash
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/botname
DISCORD_TOKEN=your_token
OPENROUTER_API_KEY_1=your_key
```

When `MONGO_URI` is set → Uses MongoDB  
When empty → Uses local SQLite

---

## 💡 Why MongoDB Works on Render

1. **External Service** - Stored outside Render container
2. **Persistent** - Survives container restarts
3. **Scalable** - Works with multiple bot instances
4. **Free Tier** - MongoDB Atlas has generous free plan

---

## 📞 Troubleshooting

### "Connection refused" error
- Check MongoDB is running (if local)
- Check MongoDB URI is correct
- Check firewall allows connections
- Check IP whitelist on MongoDB Atlas

### Data not showing up
- Verify migration script ran successfully
- Check MongoDB for data: `db.alliance_members.find()`
- Check environment variable is set on Render
- Bot needs to restart to pick up new `MONGO_URI`

### Want to switch back to SQLite?
- Just remove/clear `MONGO_URI` environment variable
- Bot falls back to local SQLite

---

## 🎯 Next Steps

1. ✅ Run `python db_migration_tool.py`
2. ✅ Create MongoDB Atlas account (free tier is fine)
3. ✅ Run `python migrate_to_mongo.py <YOUR_URI>`
4. ✅ Add `MONGO_URI` to Render environment
5. ✅ Deploy and verify data is there!

**Your data will be safe and persistent!** 🔐

---

Last Updated: November 12, 2025
