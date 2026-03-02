import asyncio
import contextlib
from app.main import app

async def test():
    try:
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(app.router.lifespan_context(app))
            print("Lifespan started successfully")
    except RuntimeError as e:
        print("RuntimeError:", e)

asyncio.run(test())
