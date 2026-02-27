import asyncio
import os
import logging
from app.config.database import AsyncSessionLocal
from app.utils.scope_engine import generate_project_scope
from app.models import Project

import uuid

logging.basicConfig(level=logging.INFO)

async def test_confidence_score():
    print("\n--- Testing Confidence Scoring Pipeline ---")
    async with AsyncSessionLocal() as db:
        # Create a mock user for owner_id constraint
        from app.models import User
        dummy_user_id = str(uuid.uuid4())
        user = User(
            id=dummy_user_id,
            email=f"test{dummy_user_id[:4]}@test.com",
            username=f"tester{dummy_user_id[:4]}",
            hashed_password="dummy",
            is_active=True,
            is_superuser=False,
            is_verified=True
        )
        db.add(user)
        
        # Create a mock project
        project = Project(
            id=str(uuid.uuid4()),
            name="Testing Confidence Script",
            domain="Data Engineering",
            complexity="High",
            duration="6",
            owner_id=dummy_user_id
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        print("Generating project scope... (this will use RAG and Benchmarks under the hood)")
        try:
            scope = await generate_project_scope(db, project)
            print("\n✅ Generation Complete!")
            
            print(f"\nScore output: {scope.get('confidence_score')}")
            for r in scope.get("confidence_reasons", []):
                print(f" - {r}")
                
            print(f"\nAny benchmark warnings?: {scope.get('_warnings', [])}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_confidence_score())
