import asyncio
import json
import logging
import sys
from app.utils import azure_blob
from app.config.database import AsyncSessionLocal
from app import models
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = "ecf43b71-c27f-4bd2-8539-a0e76b8114bd"

async def check_project():
    try:
        pid = UUID(PROJECT_ID)
    except:
        logger.error(f"Invalid UUID: {PROJECT_ID}")
        return

    logger.info(f"Checking project {pid}...")
    
    # 1. Check DB Scope
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Project)
            .where(models.Project.id == pid)
            .options(selectinload(models.Project.files))
        )
        project = result.scalar_one_or_none()
        if not project:
            logger.error("Project not found in DB")
            return
            
        logger.info(f"Project Name: {project.name}")
        
        # Check files in DB
        logger.info("--- Project Files (DB) ---")
        for f in project.files:
            logger.info(f"  - {f.file_name} ({f.file_path})")
            
    # 2. Check Finalized Scope Blob
    scope_path = f"projects/{pid}/finalized_scope.json"
    if await azure_blob.blob_exists(scope_path):
        logger.info(f"\n--- Scope Data ({scope_path}) ---")
        data = await azure_blob.download_bytes(scope_path)
        scope = json.loads(data)
        
        arch_path = scope.get("architecture_diagram")
        logger.info(f"  scope['architecture_diagram']: {arch_path}")
        
        if arch_path:
            exists = await azure_blob.blob_exists(arch_path)
            logger.info(f"  -> Blob Exists? {exists}")
            
    else:
        logger.error(f"Finalized scope blob not found at {scope_path}")

    # 3. List relevant blobs
    logger.info(f"\n--- Listing Blobs in projects/{pid}/ ---")
    blobs = await azure_blob.list_blobs(f"projects/{pid}/")
    for b in blobs:
        logger.info(f"  - {b}")

if __name__ == "__main__":
    asyncio.run(check_project())
