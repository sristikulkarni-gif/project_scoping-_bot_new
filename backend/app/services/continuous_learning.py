

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
    
    # Automatic Timeline Tracking (Option 1)
    # Start Date: When scope was finalized (or created_at fallback)
    # End Date: Now (when closeout is happening)
    
    start_dt = project.scope_finalized_at or project.created_at
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    
    project_start_date = start_dt.strftime("%Y-%m-%d") if start_dt else "N/A"
    project_end_date = end_dt.strftime("%Y-%m-%d")
    
    learning_text = (
        f"PROJECT CLOSEOUT REPORT: {project.name}\n"
        f"TYPE: ACTUAL_DATA\n"
        f"INDUSTRY: {project.domain}\n"
        f"COMPLEXITY: {project.complexity}\n"
        f"TECH STACK: {project.tech_stack}\n\n"
        f"PROJECT TIMELINE:\n"
        f"ACTUAL START DATE: {project_start_date}\n"
        f"ACTUAL END DATE: {project_end_date}\n\n"
        f"RESOURCE UTILIZATION (ACTUAL VS ESTIMATED):\n"
    )

    # Calculate max actual effort for implied duration hint
    max_act_effort = 0.0
    for r in actuals.get("resources", []):
        val = r.get('actual_effort_months', 0)
        if val > max_act_effort:
            max_act_effort = val
            
    if max_act_effort > 0:
        # Safer injection: insert before RESOURCE UTILIZATION header
        split_marker = "RESOURCE UTILIZATION (ACTUAL VS ESTIMATED):\n"
        if split_marker in learning_text:
            learning_text = learning_text.replace(split_marker, f"IMPLIED DURATION (MAX RESOURCE EFFORT): {max_act_effort} months\n\n{split_marker}")

    # Process resource-level actuals
    for resource in actuals.get("resources", []):
        est_effort = resource.get('estimated_effort_months', 0)
        act_effort = resource.get('actual_effort_months', 0)
        variance = ((act_effort - est_effort) / est_effort * 100) if est_effort > 0 else 0
        
        learning_text += (
            f"- Resource: {resource['name']}\n"
            f"  Rate: ${resource.get('rate_per_month', 0)}/month\n"
            f"  Estimated Effort: {est_effort} months\n"
            f"  ACTUAL EFFORT: {act_effort} months ({variance:+.1f}% variance)\n"
            f"  Estimated Cost: ${resource.get('estimated_cost', 0)}\n"
            f"  ACTUAL COST: ${resource.get('actual_cost', 0)}\n"
            f"  Notes: {resource.get('notes', 'N/A')}\n\n"
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
