"""
Presenton integration router for AI presentation generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config.database import get_async_session
from app.auth.router import fastapi_users
from app import models
from app.utils.presenton_client import presenton_client
from app.utils import azure_blob
from uuid import UUID
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/presenton", tags=["Presenton"])

# Get current active user dependency
current_active_user = fastapi_users.current_user(active=True)


@router.get("/health")
async def check_presenton_health():
    """
    Check if Presenton service is available and running.
    
    Returns:
        {
            "status": "available" | "unavailable",
            "url": "http://localhost:5000"
        }
    """
    is_healthy = await presenton_client.health_check()
    return {
        "status": "available" if is_healthy else "unavailable",
        "url": presenton_client.get_external_url(),
        "message": "Presenton is running" if is_healthy else "Presenton is not accessible"
    }


@router.post("/generate/{project_id}")
async def generate_with_presenton(
    project_id: UUID,
    n_slides: int = 10,
    template: str = "general",
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(current_active_user)
):
    """
    Generate presentation using Presenton from project scope data.
    
    Args:
        project_id: UUID of the project
        n_slides: Number of slides to generate (default: 10)
        template: Template name (default: "general")
    
    Returns:
        {
            "status": "success",
            "presenton_id": "uuid",
            "edit_url": "http://localhost:5000/presentation?id=uuid",
            "message": "Presentation generated successfully"
        }
    """
    # Load project
    result = await db.execute(
        select(models.Project).filter(
            models.Project.id == project_id,
            models.Project.owner_id == current_user.id
        )
    )
    project = result.scalars().first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Load finalized scope
    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
    )
    scope_file = result.scalars().first()
    
    if not scope_file:
        raise HTTPException(
            status_code=404,
            detail="No finalized scope found. Please finalize the scope first."
        )
    
    # Download and parse scope data
    try:
        scope_bytes = await azure_blob.download_bytes(scope_file.file_path)
        scope_data = json.loads(scope_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to load scope data: {e}")
        raise HTTPException(status_code=500, detail="Failed to load scope data")
    
    # Check Presenton availability
    if not await presenton_client.health_check():
        raise HTTPException(
            status_code=503,
            detail="Presenton service is not available. Please ensure it's running."
        )
    
    # Generate presentation with Presenton
    try:
        result = await presenton_client.generate_presentation(
            scope_data=scope_data,
            n_slides=n_slides,
            template=template
        )
        
        edit_url = presenton_client.get_edit_url(result["presentation_id"])
        
        return {
            "status": "success",
            "presenton_id": result["presentation_id"],
            "edit_url": edit_url,
            "file_path": result.get("path"),
            "message": "Presentation generated successfully! Click the link to edit in Presenton."
        }
    
    except Exception as e:
        logger.error(f"Presenton generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate presentation: {str(e)}"
        )


@router.get("/info")
async def get_presenton_info():
    """
    Get information about Presenton integration.
    
    Returns:
        Information about Presenton features and access
    """
    return {
        "name": "Presenton",
        "description": "Open-source AI presentation generator with templates and editing",
        "url": presenton_client.get_external_url(),
        "features": [
            "Custom templates & themes",
            "AI template generation",
            "Live slide editor",
            "PPTX & PDF export",
            "Charts & icons support",
            "Multiple AI providers"
        ],
        "documentation": "https://docs.presenton.ai"
    }
