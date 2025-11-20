# Database Path Fix for Render Deployment

## Problem
When deploying to Render, many buttons inside `/settings` were showing "you don't have permission" errors, even though the same code worked fine locally.

## Root Cause
The issue was caused by **relative database paths** in the cog files:

```python
# OLD CODE (problematic)
self.conn_settings = sqlite3.connect('db/settings.sqlite')
```

### Why This Failed on Render:
1. **Relative paths resolve differently** depending on the current working directory
2. On Render, the working directory might be different from local development
3. The SQLite databases were either:
   - Not being found (file not found errors)
   - Being created in the wrong location
   - Empty/uninitialized (no admin records)
4. Even though the code checked `mongo_enabled()`, the SQLite connections were still being used as fallback

## Solution
Created a centralized database utility module (`db_utils.py`) that provides:
1. **Absolute path resolution** - Always finds the correct `db/` directory
2. **Consistent database connections** - All cogs use the same path logic
3. **Automatic directory creation** - Ensures `db/` folder exists

### New Approach:
```python
# NEW CODE (fixed)
from db_utils import get_db_connection

self.conn_settings = get_db_connection('settings.sqlite')
```

## Files Modified

### 1. Created `db_utils.py`
- Provides `get_db_path()` - Returns absolute path to database file
- Provides `get_db_connection()` - Returns SQLite connection with correct path
- Ensures `db/` directory exists before connecting

### 2. Updated `cogs/alliance.py`
- Imports and uses `get_db_connection()` from `db_utils`
- Includes fallback implementation if `db_utils` is not available
- All database connections now use absolute paths

## Files That Still Need Updates
The following cog files still use relative paths and should be updated:

### High Priority (Used by /settings):
- `cogs/bot_operations.py` - Lines 14, 16, 155, 260, 671, 1231
- `cogs/gift_operations.py` - Lines 109, 524, 2385
- `cogs/alliance_member_operations.py` - Multiple lines

### Medium Priority:
- `cogs/attendance.py`
- `cogs/bear_trap.py`
- `cogs/changes.py`
- `cogs/control.py`
- `cogs/id_channel.py`
- `cogs/minister_menu.py`
- `cogs/minister_schedule.py`
- `cogs/wel.py`

## How to Update Other Cogs

### Step 1: Add import at the top of the file
```python
try:
    from db_utils import get_db_connection
except ImportError:
    from pathlib import Path
    import sqlite3
    def get_db_connection(db_name: str, **kwargs):
        repo_root = Path(__file__).resolve().parents[1]
        db_dir = repo_root / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(db_dir / db_name), **kwargs)
```

### Step 2: Replace all instances of:
```python
# OLD
sqlite3.connect('db/settings.sqlite')

# NEW
get_db_connection('settings.sqlite')
```

### Step 3: For context managers:
```python
# OLD
with sqlite3.connect('db/settings.sqlite') as settings_db:
    ...

# NEW
with get_db_connection('settings.sqlite') as settings_db:
    ...
```

## Testing
After deployment to Render:
1. Run `/settings` command
2. Click on each button (Alliance Operations, Bot Operations, etc.)
3. Verify no "permission denied" errors
4. Check that admin permissions are properly recognized

## MongoDB vs SQLite
- The bot prefers MongoDB when `MONGO_URI` is set
- SQLite is used as fallback when MongoDB is unavailable
- This fix ensures SQLite works correctly in both environments
- The permission checks now work regardless of which backend is active

## Deployment Notes
- Commit and push these changes to your Git repository
- Render will automatically detect and redeploy
- No environment variable changes needed
- The fix is backward compatible with local development
