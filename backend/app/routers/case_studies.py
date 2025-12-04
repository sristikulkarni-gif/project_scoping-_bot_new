"""
API endpoints for managing pending generated case studies.
"""
import uuid
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app import models
from app.config.database import get_async_session
from app.auth.router import fastapi_users
from app.utils.case_study_management import approve_case_study, reject_case_study

# Auth dependencies
get_current_active_user = fastapi_users.current_user(active=True)
get_current_superuser = fastapi_users.current_user(active=True, superuser=True)

router = APIRouter(prefix="/api/case_studies", tags=["case_studies"])
logger = logging.getLogger(__name__)


# Schemas
class ApprovalRequest(BaseModel):
    admin_comment: str | None = None


class CaseStudyResponse(BaseModel):
    id: str
    project_id: str
    client_name: str
    project_title: str
    overview: str
    solution: str
    impact: str
    file_name: str
    blob_path: str
    status: str
    generated_by_llm: bool
    created_at: str
    reviewed_at: str | None = None
    admin_comment: str | None = None


@router.get("/pending", response_model=List[CaseStudyResponse])
async def list_pending_case_studies(
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_superuser)  # Only admins/superusers
):
    """
    List all pending generated case studies awaiting approval.
    Requires admin/superuser privileges.
    """
    try:
        result = await db.execute(
            select(models.PendingGeneratedCaseStudy)
            .where(models.PendingGeneratedCaseStudy.status == "pending")
            .order_by(models.PendingGeneratedCaseStudy.created_at.desc())
        )
        pending_case_studies = result.scalars().all()

        return [
            CaseStudyResponse(
                id=str(cs.id),
                project_id=str(cs.project_id),
                client_name=cs.client_name,
                project_title=cs.project_title,
                overview=cs.overview,
                solution=cs.solution,
                impact=cs.impact,
                file_name=cs.file_name,
                blob_path=cs.blob_path,
                status=cs.status,
                generated_by_llm=cs.generated_by_llm,
                created_at=cs.created_at.isoformat(),
                reviewed_at=cs.reviewed_at.isoformat() if cs.reviewed_at else None,
                admin_comment=cs.admin_comment
            )
            for cs in pending_case_studies
        ]

    except Exception as e:
        logger.error(f"Failed to list pending case studies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{pending_id}/approve")
async def approve_pending_case_study(
    pending_id: uuid.UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_superuser)  # Only admins/superusers
):
    """
    Approve a pending generated case study.
    This will:
    1. Move the PDF to the main case_studies folder
    2. Create a KnowledgeBaseDocument entry
    3. Vectorize and store in Qdrant
    4. Mark the pending record as approved

    Requires admin/superuser privileges.
    """
    try:
        result = await approve_case_study(
            pending_id=pending_id,
            admin_user_id=current_user.id,
            db=db,
            admin_comment=request.admin_comment
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve case study: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{pending_id}/reject")
async def reject_pending_case_study(
    pending_id: uuid.UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_superuser)  # Only admins/superusers
):
    """
    Reject a pending generated case study.
    This will:
    1. Delete the PDF from the pending folder
    2. Mark the pending record as rejected

    Requires admin/superuser privileges.
    """
    try:
        result = await reject_case_study(
            pending_id=pending_id,
            admin_user_id=current_user.id,
            db=db,
            admin_comment=request.admin_comment or "Rejected by admin"
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reject case study: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pending_id}", response_model=CaseStudyResponse)
async def get_pending_case_study(
    pending_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_superuser)  # Only admins/superusers
):
    """
    Get details of a specific pending case study.
    Requires admin/superuser privileges.
    """
    try:
        result = await db.execute(
            select(models.PendingGeneratedCaseStudy)
            .where(models.PendingGeneratedCaseStudy.id == pending_id)
        )
        cs = result.scalar_one_or_none()

        if not cs:
            raise HTTPException(status_code=404, detail="Pending case study not found")

        return CaseStudyResponse(
            id=str(cs.id),
            project_id=str(cs.project_id),
            client_name=cs.client_name,
            project_title=cs.project_title,
            overview=cs.overview,
            solution=cs.solution,
            impact=cs.impact,
            file_name=cs.file_name,
            blob_path=cs.blob_path,
            status=cs.status,
            generated_by_llm=cs.generated_by_llm,
            created_at=cs.created_at.isoformat(),
            reviewed_at=cs.reviewed_at.isoformat() if cs.reviewed_at else None,
            admin_comment=cs.admin_comment
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pending case study: {e}")
        raise HTTPException(status_code=500, detail=str(e))