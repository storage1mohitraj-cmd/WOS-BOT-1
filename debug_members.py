"""
Debug script to check MongoDB status and member data location
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

print("=" * 60)
print("MongoDB and Member Data Debug")
print("=" * 60)
print()

# Check MongoDB status
try:
    from db.mongo_adapters import mongo_enabled, AllianceMembersAdapter
    print(f"✅ MongoDB adapters imported successfully")
    print(f"📊 MongoDB enabled: {mongo_enabled()}")
    print()
    
    if mongo_enabled():
        print("🔍 Checking MongoDB for members...")
        try:
            docs = AllianceMembersAdapter.get_all_members()
            if docs:
                print(f"   Found {len(docs)} members in MongoDB")
                # Group by alliance
                from collections import defaultdict
                by_alliance = defaultdict(int)
                for d in docs:
                    alliance_id = d.get('alliance') or d.get('alliance_id') or 0
                    by_alliance[alliance_id] += 1
                
                print("   Members per alliance in MongoDB:")
                for alliance_id, count in sorted(by_alliance.items()):
                    print(f"      Alliance {alliance_id}: {count} members")
            else:
                print("   ⚠️  MongoDB returned empty list or None")
        except Exception as e:
            print(f"   ❌ Error querying MongoDB: {e}")
    else:
        print("ℹ️  MongoDB is disabled, using SQLite fallback")
        
except Exception as e:
    print(f"❌ Error importing MongoDB adapters: {e}")
    print("   Falling back to SQLite only")

print()
print("-" * 60)
print()

# Check SQLite
import sqlite3
db_path = Path(__file__).resolve().parent / "db" / "users.sqlite"

if db_path.exists():
    print("🔍 Checking SQLite for members...")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    print(f"   Total users in SQLite: {total}")
    
    cursor.execute("SELECT alliance, COUNT(*) FROM users GROUP BY alliance ORDER BY COUNT(*) DESC")
    results = cursor.fetchall()
    
    if results:
        print("   Members per alliance in SQLite:")
        for alliance_id, count in results:
            print(f"      Alliance {alliance_id}: {count} members")
    
    conn.close()
else:
    print(f"❌ SQLite database not found at: {db_path}")

print()
print("=" * 60)
