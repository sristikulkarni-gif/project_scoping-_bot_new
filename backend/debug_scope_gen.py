import asyncio
import os
import sys
from sqlalchemy import select

sys.path.append(os.getcwd())

from app.config.database import AsyncSessionLocal
from app import models
from app.utils.scope_engine import generate_project_scope

async def test_scope_gen():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(models.Project).order_by(models.Project.created_at.desc()))
        project = result.scalars().first()
        if not project:
            print("No projects found.")
            return

        print(f"Testing scope generation for project: {project.name} ({project.id})")
        
        try:
            scope = await generate_project_scope(session, project)
            print("Scope generated successfully:")
            print(scope)
        except Exception as e:
            print(f"Error generating scope: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scope_gen())
