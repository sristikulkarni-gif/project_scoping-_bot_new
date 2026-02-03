

import logging
import json
import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
from app.services import rag_service

logger = logging.getLogger(__name__)

async def process_project_closeout(
    project_id: uuid.UUID,
    actuals: dict,
    db: AsyncSession
):
    """
    Ingests 'Actual' project data into the Knowledge Base for continuous learning.
    """
    logger.info(f"🔄 Processing closeout for project {project_id}")

    # 1. Fetch Project Data
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise ValueError("Project not found")

    # 2. Construct the 'Learning Document'
    # This text format is optimized for retrieval by the Scoping Engine
    learning_text = (
        f"PROJECT CLOSEOUT REPORT: {project.name}\n"
        f"TYPE: ACTUAL_DATA\n"
        f"INDUSTRY: {project.domain}\n"
        f"COMPLEXITY: {project.complexity}\n\n"
        f"DESCRIPTION:\n{project.description if hasattr(project, 'description') else 'N/A'}\n\n"
        f"ACTUAL RESULTS (VS ESTIMATES):\n"
    )

    for act in actuals.get("activities", []):
        learning_text += (
            f"- Activity: {act['name']}\n"
            f"  Estimated Duration: {act.get('estimated_duration', 'N/A')}\n"
            f"  ACTUAL DURATION: {act['actual_duration']}\n"
            f"  Note: {act.get('notes', '')}\n"
        )

    # 3. Create a Knowledge Base Entry associated with this memory
    kb_id = uuid.uuid4()
    
    # Store in Qdrant (RAG)
    try:
        # We manually chunk it as one meaningful unit or small chunks
        # ideally we keep the closeout report relatively atomic for retrieval
        await rag_service.vectorize_text(
            text=learning_text,
            metadata={
                "source": "continuous_learning",
                "project_id": str(project_id),
                "type": "actual_data", # CRITICAL tag for the prompt
                "industry": project.domain,
                "document_id": str(kb_id)
            }
        )
        logger.info(f"✅ Vectorized Closeout Report for {project.name}")
        
        # 4. (Optional) Store as a PDF/File in 'knowledge_base/learned' blob path so it shows in UI
        # For now, we just ensure it's in the vector DB which is what matters for the AI.

        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to vectorize learning data: {e}")
        raise e
