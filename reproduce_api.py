import aiohttp
import asyncio
import hashlib
import time
import json
import ssl

API_URL = "https://wos-giftcode-api.centurygame.com/api/player"
SECRET = "tB87#kPtkxqOS2"

async def main():
    fid = "492796533"
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://wos-giftcode-api.centurygame.com",
    }
    
    current_time = int(time.time() * 1000)
    form = f"fid={fid}&time={current_time}"
    sign = hashlib.md5((form + SECRET).encode("utf-8")).hexdigest()
    payload = f"sign={sign}&{form}"
    
    print(f"Fetching info for {fid}...")
    
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(API_URL, data=payload, headers=headers, timeout=20) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                try:
                    js = json.loads(text)
                    print("JSON Response Keys in 'data':")
                    if 'data' in js:
                        for k, v in js['data'].items():
                            print(f"{k}: {v}")
                    else:
                        print(js)
                except Exception as e:
                    print("Could not parse JSON:")
                    print(text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
