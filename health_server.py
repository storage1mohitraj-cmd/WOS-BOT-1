import os
from aiohttp import web
from datetime import datetime

async def start_health_server():
    port = int(os.environ.get('PORT', '8080'))
    app = web.Application()

    async def handle_root(request):
        return web.Response(text='OK', content_type='text/plain')

    async def handle_health(request):
        return web.json_response({
            'status': 'ok',
            'time': datetime.utcnow().isoformat()
        })

    app.add_routes([
        web.get('/', handle_root),
        web.get('/health', handle_health)
    ])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Keep running until canceled; aiohttp site runs in background on the loop
    return port
