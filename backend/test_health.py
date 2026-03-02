import asyncio
from app.routers.presenton import check_presenton_health

async def main():
    try:
        res = await check_presenton_health()
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
