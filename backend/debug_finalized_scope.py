import asyncio
import sys
import os

# Ensure backend path is in sys.path
sys.path.append(os.getcwd())

from app.config.database import AsyncSessionLocal, AsyncSession
from sqlalchemy import select
from app import models
from app.utils import azure_blob
import uuid
import json

async def debug():
    project_id = uuid.UUID("f40aa040-6cde-464a-89cb-3c540a25a6b5")
    try:
        async with AsyncSessionLocal() as db:
            print(f"Checking project {project_id}...")
            
            # Check ProjectFile
            stmt = select(models.ProjectFile).filter(
                models.ProjectFile.project_id == project_id,
                models.ProjectFile.file_name == "finalized_scope.json"
            )
            result = await db.execute(stmt)
            pf = result.scalars().first()
            
            if not pf:
                print("❌ No ProjectFile record found for finalized_scope.json")
                return
                
            print(f"✅ Found ProjectFile: {pf.file_path}")
            
            # Check Blob
            exists = await azure_blob.blob_exists(pf.file_path)
            print(f"Blob exists: {exists}")
            
            if exists:
                try:
                    print("Downloading blob...")
                    data = await azure_blob.download_bytes(pf.file_path)
                    print(f"Downloaded {len(data)} bytes")
                    json_data = json.loads(data.decode("utf-8"))
                    print("✅ JSON parsed successfully")
                except Exception as e:
                    print(f"❌ Failed to download/parse blob: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                 print("❌ Blob does not exist in Azure Storage")

    except Exception as e:
        print(f"❌ DB Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
