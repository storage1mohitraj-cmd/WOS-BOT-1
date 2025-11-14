# MongoDB Connection Fix for Render Deployment

## Issue Summary
Your Discord bot on Render is failing to import the MongoDB adapters:
```
❌ Failed to import GiftCodesAdapter: No module named 'db.mongo_adapters'
❌ Failed to initialize MongoDB storage via db.* and fallback, falling back to SQLite
```

## Root Cause
The `db` package module is not being found on Render during import. This is a common issue when deploying to cloud platforms due to working directory differences and Python path resolution.

---

## Changes Made

### 1. **Updated `db/mongo_adapters.py`**
   - ✅ Added explicit `__all__` export list to ensure all adapters are properly exported
   - This ensures the module exports work correctly on all platforms (local, Docker, Render)

### 2. **Updated `mongo_adapters.py` (top-level shim)**
   - ✅ Added `AllianceMembersAdapter` to the `__all__` list
   - ✅ Added fallback class `AllianceMembersAdapter` for when MongoDB is unavailable
   - ✅ Enhanced error logging to show import failure reasons

### 3. **Updated `render.yaml`**
   - ✅ Added environment variables for MongoDB connection tuning:
     - `MONGO_CONNECT_TIMEOUT_MS=60000` (60 seconds - increased from default 30s)
     - `MONGO_CONNECT_RETRIES=5` (5 retries with exponential backoff)
   - ✅ Added `PYTHONPATH=/opt/render/project` to help Python find the `db` package
   - ✅ Added `PYTHONUNBUFFERED=1` for real-time logging on Render

### 4. **Created `test_mongo_imports.py`**
   - A comprehensive diagnostic script to test imports and MongoDB connectivity
   - Use this to debug any remaining issues

---

## Troubleshooting Steps

### Step 1: Deploy and Check Logs
1. Commit these changes: `git add . && git commit -m "Fix MongoDB import issues on Render" && git push origin main`
2. Wait for Render to rebuild and redeploy
3. Go to your Render service dashboard → **Logs** tab
4. Look for error messages about MongoDB connection

### Step 2: Run Diagnostics on Render (if still failing)
1. Add this to your Render dashboard for testing:
   ```bash
   python test_mongo_imports.py
   ```

### Step 3: Verify MongoDB Atlas Configuration
1. **Allow Render's IP**: In MongoDB Atlas → Network Access → Add IP
   - Add `0.0.0.0/0` (allow all) OR look up Render's IP
   - Singapore region Render IPs may vary, so "allow all" is easiest for testing

2. **Check MONGO_URI Format**: Should look like:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
   ```
   - Replace special characters in username/password with URL-encoded versions
   - Example: `@` becomes `%40`, `/` becomes `%2F`

3. **Verify Credentials**: Make sure username/password is correct and user has appropriate permissions

---

## MongoDB Connection String Best Practices

### If using MongoDB Atlas:
```
mongodb+srv://[username]:[password]@[cluster].mongodb.net/[database]?retryWrites=true&w=majority
```

### Important:
- Username/password must be URL-encoded (use MongoDB Atlas's generated connection string directly)
- The connection string includes automatic retry logic
- The replica set is configured automatically for Atlas

---

## Expected Behavior After Fix

### Before:
```
❌ Failed to import GiftCodesAdapter: No module named 'db.mongo_adapters'
ℹ️ MongoDB not configured - Falling back to SQLite
```

### After (if MongoDB connection succeeds):
```
ℹ️ ✅ MONGO_URI detected - Using MongoDB for ALL data persistence
ℹ️ ✅ MongoDB enabled - Using GiftCodesAdapter for all operations
✅ Successfully connected to MongoDB
```

---

## If MongoDB Still Fails to Connect

The bot will gracefully fall back to SQLite. This means:
- ✅ Bot will continue to work with local SQLite databases
- ⚠️ Data won't persist across container restarts on Render
- 🔧 You can fix this by:
  1. Checking MongoDB Atlas network access
  2. Verifying MONGO_URI environment variable is set correctly
  3. Running `test_mongo_imports.py` to diagnose exact error

---

## Render Environment Setup Checklist

- [ ] Verify MONGO_URI is set as an environment variable (not synced from GitHub)
- [ ] Verify MongoDB Atlas allows connections from Render IPs (0.0.0.0/0 or specific IP)
- [ ] Verify MONGO_DB_NAME matches your MongoDB database name
- [ ] Verify username/password in connection string are URL-encoded if needed
- [ ] Check Render logs for specific MongoDB connection errors
- [ ] Test with `python test_mongo_imports.py`

---

## Files Modified

1. ✅ `db/mongo_adapters.py` - Added `__all__` export list
2. ✅ `mongo_adapters.py` - Enhanced shim with better exports and error handling
3. ✅ `render.yaml` - Added MongoDB connection tuning and PYTHONPATH
4. ✅ `test_mongo_imports.py` - New diagnostic script (created)

---

## Next Steps

1. Push changes to GitHub
2. Let Render redeploy
3. Check logs for errors
4. If still failing, run the diagnostic script and check MongoDB Atlas network settings
