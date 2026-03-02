
import asyncio
import sys
import os
from sqlalchemy import select

# Setup path
sys.path.append(os.getcwd())

from app.config.database import AsyncSessionLocal
from app import models

async def list_projects():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(models.Project))
        projects = result.scalars().all()
        print(f"Found {len(projects)} projects.")
        for p in projects:
            print(f"ID: {p.id} | Name: {p.name}")

if __name__ == "__main__":
    asyncio.run(list_projects())
