import asyncio
from search_utils import fetch_search_results

async def main():
    res = await fetch_search_results('time in India', max_results=3)
    print('Got', len(res), 'results')
    for r in res:
        print('-', r.get('title') or r.get('text'))
        print('  ', r.get('href') or r.get('url') or r.get('link'))

if __name__ == '__main__':
    asyncio.run(main())
