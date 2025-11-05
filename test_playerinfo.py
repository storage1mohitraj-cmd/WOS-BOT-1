import asyncio
from wos_api import fetch_player_info

async def main():
    pid = "492796533"
    try:
        info = await fetch_player_info(pid)
        print("FETCHED INFO:")
        print(info)
    except Exception as e:
        print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
