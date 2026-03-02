
import asyncio
import sys
import os
import uuid
from app.config.database import AsyncSessionLocal
from app.services.continuous_learning import process_project_closeout

# Setup path
sys.path.append(os.getcwd())

async def run_closeout():
    project_id = uuid.UUID("cfa18846-461b-409a-b81a-da7b51360249")
    payload = {
        "activities": [
            {
                "name": "Requirement Gathering",
                "estimated_duration": "2 weeks",
                "actual_duration": "3 weeks",
                "notes": "Client availability was low"
            }
        ]
    }
    
    print(f"--- Running Closeout for Project {project_id} ---")
    
    try:
        async with AsyncSessionLocal() as session:
            await process_project_closeout(project_id, payload, session)
        print("✅ Success! No errors.")
    except Exception as e:
        print(f"❌ Error caught: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_closeout())
