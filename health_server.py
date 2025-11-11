import os
from aiohttp import web
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

async def start_health_server():
    """Start a lightweight HTTP server for health checks.

    Returns the port on success, or None if the server could not be started
    (for example, because the port is already in use).
    """
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
    try:
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        try:
            await site.start()
        except OSError as e:
            # Port likely in use; log and return None so caller can continue
            logger.warning(f"Health server could not bind to 0.0.0.0:{port}: {e}")
            # Attempt to clean up runner
            try:
                await runner.cleanup()
            except Exception:
                pass
            return None
    except Exception as e:
        logger.exception(f"Failed to start health server: {e}")
        try:
            await runner.cleanup()
        except Exception:
            pass
        return None

    # Keep running until canceled; aiohttp site runs in background on the loop
    return port
