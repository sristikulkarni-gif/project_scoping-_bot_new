"""
Management functions for pending generated case studies - approve/reject workflow.
"""
import logging
import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import models
from app.utils import azure_blob
from app.utils.scope_engine import extract_text_from_file
from app.utils.ai_clients import embed_text_ollama, get_qdrant_client
from app.config.config import CASE_STUDY_COLLECTION

logger = logging.getLogger(__name__)


async def approve_case_study(
    pending_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    db: AsyncSession,
    admin_comment: str = None
) -> Dict[str, Any]:
    """
    Approve a pending generated case study and move it to the main knowledge base.

    Steps:
    1. Move PDF from knowledge_base/pending/ to knowledge_base/case_studies/
    2. Create KnowledgeBaseDocument entry
    3. Extract text from PDF
    4. Generate embeddings
    5. Store in Qdrant
    6. Update pending record status

    Args:
        pending_id: ID of pending case study
        admin_user_id: ID of admin approving
        db: Database session
        admin_comment: Optional comment from admin

    Returns:
        Dictionary with status and approved document info
    """
    try:
        # Get pending case study
        result = await db.execute(
            select(models.PendingGeneratedCaseStudy).where(
                models.PendingGeneratedCaseStudy.id == pending_id
            )
        )
        pending = result.scalar_one_or_none()

        if not pending:
            raise ValueError(f"Pending case study {pending_id} not found")

        if pending.status != "pending":
            raise ValueError(f"Case study already {pending.status}")

        logger.info(f"📋 Approving case study: {pending.client_name} - {pending.project_title}")

        # 1. Download PDF from pending folder
        pdf_bytes = await azure_blob.download_bytes(pending.blob_path, "knowledge_base")

        # 2. Create new blob path in case_studies folder
        approved_blob_name = f"case_studies/{pending.file_name}"

        # 3. Upload to case_studies folder
        await azure_blob.upload_bytes(pdf_bytes, approved_blob_name, "knowledge_base")
        logger.info(f"✅ Moved PDF: {pending.blob_path} → {approved_blob_name}")

        # 4. Create or Update KnowledgeBaseDocument entry
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Check if it already exists to avoid unique constraint violation
        existing_kb_result = await db.execute(
            select(models.KnowledgeBaseDocument).where(
                models.KnowledgeBaseDocument.blob_path == approved_blob_name
            )
        )
        existing_kb = existing_kb_result.scalar_one_or_none()

        if existing_kb:
            logger.info(f"⚠️ KB Document already exists for {approved_blob_name}, updating it.")
            kb_document = existing_kb
            kb_document.file_hash = file_hash
            kb_document.file_size = len(pdf_bytes)
            kb_document.case_study_metadata = json.dumps({
                "client_name": pending.client_name,
                "overview": pending.overview,
                "solution": pending.solution,
                "impact": pending.impact,
                "generated_by_llm": True,
                "approved_at": datetime.utcnow().isoformat()
            })
            # Reset vectorization status as we are re-processing
            kb_document.is_vectorized = False
            kb_document.vector_count = 0
        else:
            kb_document = models.KnowledgeBaseDocument(
                id=uuid.uuid4(),
                file_name=pending.file_name,
                blob_path=approved_blob_name,
                file_hash=file_hash,
                file_size=len(pdf_bytes),
                document_type="case_study",
                case_study_metadata=json.dumps({
                    "client_name": pending.client_name,
                    "overview": pending.overview,
                    "solution": pending.solution,
                    "impact": pending.impact,
                    "generated_by_llm": True,
                    "approved_at": datetime.utcnow().isoformat()
                }),
                is_vectorized=False,
                vector_count=0
            )
            db.add(kb_document)
        
        await db.flush()

        logger.info(f"✅ KB document ID: {kb_document.id}")

        # 5. Extract text from PDF
        import io
        from PyPDF2 import PdfReader

        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"

            logger.info(f"📄 Extracted {len(text_content)} characters from PDF")
        except Exception as e:
            logger.warning(f"Failed to extract text from PDF: {e}")
            # Use case study content as fallback
            text_content = f"{pending.client_name}\n\n{pending.overview}\n\n{pending.solution}\n\n{pending.impact}"

        # 6. Generate embeddings and store in Qdrant
        await _vectorize_case_study(
            kb_document=kb_document,
            text_content=text_content,
            case_study_metadata={
                "client_name": pending.client_name,
                "overview": pending.overview,
                "solution": pending.solution,
                "impact": pending.impact
            },
            db=db
        )

        # 7. Update pending record
        pending.status = "approved"
        pending.reviewed_by = admin_user_id
        pending.reviewed_at = datetime.utcnow()
        pending.admin_comment = admin_comment
        pending.approved_document_id = kb_document.id

        await db.commit()

        logger.info(f"✅ Case study approved: {pending.client_name}")

        return {
            "status": "approved",
            "pending_id": str(pending_id),
            "document_id": str(kb_document.id),
            "blob_path": approved_blob_name,
            "message": f"Case study '{pending.client_name}' approved and added to knowledge base"
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to approve case study: {e}")
        raise


async def reject_case_study(
    pending_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    db: AsyncSession,
    admin_comment: str = None
) -> Dict[str, Any]:
    """
    Reject a pending generated case study and delete it.

    Steps:
    1. Delete PDF from pending folder
    2. Update pending record status to rejected

    Args:
        pending_id: ID of pending case study
        admin_user_id: ID of admin rejecting
        db: Database session
        admin_comment: Optional comment explaining rejection

    Returns:
        Dictionary with status
    """
    try:
        # Get pending case study
        result = await db.execute(
            select(models.PendingGeneratedCaseStudy).where(
                models.PendingGeneratedCaseStudy.id == pending_id
            )
        )
        pending = result.scalar_one_or_none()

        if not pending:
            raise ValueError(f"Pending case study {pending_id} not found")

        if pending.status != "pending":
            raise ValueError(f"Case study already {pending.status}")

        logger.info(f"❌ Rejecting case study: {pending.client_name} - {pending.project_title}")

        # 1. Delete PDF from pending folder
        try:
            await azure_blob.delete_blob(pending.blob_path, "knowledge_base")
            logger.info(f"🗑️ Deleted PDF: {pending.blob_path}")
        except Exception as e:
            logger.warning(f"Failed to delete PDF (may not exist): {e}")

        # 2. Update pending record
        pending.status = "rejected"
        pending.reviewed_by = admin_user_id
        pending.reviewed_at = datetime.utcnow()
        pending.admin_comment = admin_comment or "Rejected by admin"

        await db.commit()

        logger.info(f"✅ Case study rejected: {pending.client_name}")

        return {
            "status": "rejected",
            "pending_id": str(pending_id),
            "message": f"Case study '{pending.client_name}' rejected"
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reject case study: {e}")
        raise


async def _vectorize_case_study(
    kb_document: models.KnowledgeBaseDocument,
    text_content: str,
    case_study_metadata: Dict[str, Any],
    db: AsyncSession
) -> None:
    """
    Generate embeddings for case study and store in Qdrant.

    Args:
        kb_document: KnowledgeBaseDocument instance
        text_content: Extracted text from case study
        case_study_metadata: Case study metadata (client_name, overview, etc.)
        db: Database session
    """
    try:
        # Chunk text (use 1000 char chunks with 200 overlap)
        chunks = _chunk_text(text_content, chunk_size=1000, overlap=200)

        if not chunks:
            raise ValueError("No text chunks generated")

        logger.info(f"📦 Generated {len(chunks)} chunks for vectorization")

        # Generate embeddings
        embeddings = embed_text_ollama(chunks)

        if not embeddings or len(embeddings) != len(chunks):
            raise ValueError("Failed to generate embeddings")

        # Store in Qdrant
        qdrant_client = get_qdrant_client()

        from qdrant_client.models import PointStruct

        points = []
        point_ids = []

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)

            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "parent_id": str(kb_document.id),
                    "chunk_id": f"{kb_document.id}_{idx}",
                    "chunk_index": idx,
                    "chunk": chunk,
                    "file_name": kb_document.file_name,
                    "title": f"{case_study_metadata['client_name']} Case Study",
                    "case_study_metadata": json.dumps(case_study_metadata),
                    "document_type": "case_study"
                }
            ))

        # Upload to Qdrant
        qdrant_client.upsert(
            collection_name=CASE_STUDY_COLLECTION,
            points=points
        )

        logger.info(f"✅ Stored {len(points)} vectors in Qdrant")

        # Update KB document
        kb_document.is_vectorized = True
        kb_document.vector_count = len(points)
        kb_document.qdrant_point_ids = json.dumps(point_ids)
        kb_document.vectorized_at = datetime.utcnow()

        await db.commit()

    except Exception as e:
        logger.error(f"Failed to vectorize case study: {e}")
        raise


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks.
    """
    if not text or len(text) == 0:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks