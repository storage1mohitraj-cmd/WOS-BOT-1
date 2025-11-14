#!/usr/bin/env python3
"""
Diagnostic script to test MongoDB module imports and configuration
Run this on Render to debug import issues
"""
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(name)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 80)
print("MONGODB IMPORT DIAGNOSTICS")
print("=" * 80)

# 1. Check environment
print("\n[1] ENVIRONMENT VARIABLES")
print(f"MONGO_URI set: {bool(os.getenv('MONGO_URI'))}")
print(f"MONGO_DB_NAME: {os.getenv('MONGO_DB_NAME', 'discord_bot')}")
print(f"MONGO_CONNECT_TIMEOUT_MS: {os.getenv('MONGO_CONNECT_TIMEOUT_MS', '30000')}")
print(f"MONGO_CONNECT_RETRIES: {os.getenv('MONGO_CONNECT_RETRIES', '3')}")
print(f"CWD: {os.getcwd()}")
print(f"sys.prefix: {sys.prefix}")

# 2. Check sys.path
print("\n[2] PYTHON PATH")
for i, path in enumerate(sys.path[:10]):
    print(f"  {i}: {path}")

# 3. Check if db package exists
print("\n[3] DB PACKAGE STRUCTURE")
repo_root = os.path.dirname(__file__)
db_path = os.path.join(repo_root, 'db')
print(f"db directory exists: {os.path.isdir(db_path)}")
print(f"db/__init__.py exists: {os.path.isfile(os.path.join(db_path, '__init__.py'))}")
print(f"db/mongo_adapters.py exists: {os.path.isfile(os.path.join(db_path, 'mongo_adapters.py'))}")
print(f"db/mongo_client_wrapper.py exists: {os.path.isfile(os.path.join(db_path, 'mongo_client_wrapper.py'))}")

# 4. Test imports step by step
print("\n[4] IMPORT TESTS")

print("\n  [4a] Testing 'import db'...")
try:
    import db
    print("    ✅ SUCCESS: import db")
except Exception as e:
    print(f"    ❌ FAILED: {e}")

print("\n  [4b] Testing 'import db.mongo_adapters'...")
try:
    import db.mongo_adapters
    print("    ✅ SUCCESS: import db.mongo_adapters")
except Exception as e:
    print(f"    ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n  [4c] Testing 'from db.mongo_adapters import mongo_enabled'...")
try:
    from db.mongo_adapters import mongo_enabled
    print("    ✅ SUCCESS: from db.mongo_adapters import mongo_enabled")
    print(f"    mongo_enabled() = {mongo_enabled()}")
except Exception as e:
    print(f"    ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n  [4d] Testing 'from db.mongo_adapters import GiftCodesAdapter'...")
try:
    from db.mongo_adapters import GiftCodesAdapter
    print("    ✅ SUCCESS: from db.mongo_adapters import GiftCodesAdapter")
    print(f"    GiftCodesAdapter = {GiftCodesAdapter}")
except Exception as e:
    print(f"    ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n  [4e] Testing top-level 'mongo_adapters' shim...")
try:
    import mongo_adapters
    print("    ✅ SUCCESS: import mongo_adapters (shim)")
    print(f"    mongo_adapters.__all__ = {mongo_adapters.__all__}")
except Exception as e:
    print(f"    ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n  [4f] Testing 'from mongo_adapters import GiftCodesAdapter'...")
try:
    from mongo_adapters import GiftCodesAdapter as GCA
    print("    ✅ SUCCESS: from mongo_adapters import GiftCodesAdapter (shim)")
except Exception as e:
    print(f"    ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# 5. Test MongoDB connection
print("\n[5] MONGODB CONNECTION TEST")
mongo_uri = os.getenv('MONGO_URI')
if mongo_uri:
    print(f"  MONGO_URI detected (masked): mongodb+srv://...@...")
    try:
        from db.mongo_client_wrapper import get_mongo_client
        print("  Attempting connection...")
        client = get_mongo_client(mongo_uri)
        print("  ✅ Successfully connected to MongoDB!")
        client.close()
    except Exception as e:
        print(f"  ❌ Failed to connect: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ⚠️  MONGO_URI not set - skipping connection test")

print("\n" + "=" * 80)
print("DIAGNOSTICS COMPLETE")
print("=" * 80)
