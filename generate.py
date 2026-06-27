import aiohttp, asyncio, json

async def main():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(
            "https://cryptifo.com/api/captcha/generate",
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            print(r)
            #data = await r.json()
            #print(f"status: {r.status}")
            #print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
