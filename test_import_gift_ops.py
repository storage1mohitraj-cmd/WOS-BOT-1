import asyncio
import importlib
import sys
sys.path.insert(0, r'F:/STARK-whiteout survival bot/DISCORD BOT')

async def main():
    try:
        m = importlib.import_module('cogs.gift_operations')
        print('module imported:', m)

        class DummyBot:
            def __init__(self):
                self.extensions = {}
            async def add_cog(self, cog):
                print('add_cog called with', cog.__class__.__name__)

        bot = DummyBot()
        print('calling setup...')
        await m.setup(bot)
        print('setup finished')
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
