"""Quick test helper to check MongoDB connectivity using the repo's mongo_client_wrapper.

Run this from the repo (preferably inside the `.venv311`):
  ..\.venv311\Scripts\python.exe scripts/test_mongo_connect.py

It will print a success message or a full traceback to help debugging Atlas/network issues.
"""
import traceback
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path so sibling modules (mongo_client_wrapper) can be imported
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

# Try to load .env (if present) so tests run with the same MONGO_URI used by the app
try:
    from dotenv import load_dotenv
    dotenv_path = repo_root / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except Exception:
    # python-dotenv may not be available; tests will rely on environment variables instead
    pass

from db.mongo_client_wrapper import get_mongo_client


def main():
    try:
        print('MONGO_URI present in env:', bool(os.getenv('MONGO_URI')))
        # Use the wrapper so its retry logic is exercised
        client = get_mongo_client()
        print('Connected to MongoDB. Client nodes:', getattr(client, 'nodes', None))
        try:
            info = client.admin.command('hello') if hasattr(client.admin, 'command') else client.server_info()
            print('Server hello/server_info:', info)
        except Exception:
            # some servers may not permit 'hello'; fallback to ping
            print('Running ping...')
            client.admin.command('ping')
            print('Ping succeeded')
    except Exception:
        print('\n--- Exception while testing MongoDB connection ---')
        traceback.print_exc()


if __name__ == '__main__':
    main()
