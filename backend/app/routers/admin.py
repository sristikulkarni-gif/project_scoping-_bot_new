import uuid
import json
import logging
import os
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from qdrant_client.models import PointStruct

from app.auth.router import fastapi_users
from app import models
from app.config.database import get_async_session

from app.engine.document_processor import extract_text_from_file
from app.utils.ai_clients import embed_text_azure, get_qdrant_client
from app.utils.case_study_management import _chunk_text

logger = logging.getLogger(__name__)

# Define router
router = APIRouter(prefix="/api/admin", tags=["Admin"])
get_current_superuser = fastapi_users.current_user(active=True, superuser=True)
get_current_active_user = fastapi_users.current_user(active=True)

PAST_PROPOSALS_COLLECTION = os.getenv("PAST_PROPOSALS_COLLECTION", "past_proposals")

@router.post("/upload_sow")
async def upload_sow(
    file: UploadFile = File(...),
    client_name: str = Form(...),
    domain: str = Form(...),
    tech_stack: str = Form(""),
    duration_months: float = Form(...),
    team_size: int = Form(...),
    total_cost: float = Form(...),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Endpoint for admins to upload historical SOW/Proposal documents into the knowledge base (Qdrant).
    These will be used via RAG as few-shot calibration examples during scope generation.
    """
    logger.info(f"Uploading SOW for {client_name} - {domain} by {current_user.email}")
    try:
        # Extract Text
        file_bytes = await file.read()
        file_io = BytesIO(file_bytes)
        
        extracted_text = extract_text_from_file(file_io, file.filename)
        if not extracted_text or not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the provided file.")

        logger.info(f"📄 Extracted {len(extracted_text)} characters from SOW")

        # Chunk the text
        chunks = _chunk_text(extracted_text, chunk_size=1000, overlap=200)
        if not chunks:
            raise HTTPException(status_code=400, detail="No valid text chunks generated.")
        
        # Embed the chunks
        embeddings = embed_text_azure(chunks)
        if not embeddings or len(embeddings) != len(chunks):
            raise HTTPException(status_code=500, detail="Embedding generation failed.")

        # Store in Qdrant
        client = get_qdrant_client()
        points = []
        document_id = str(uuid.uuid4())
        
        metadata = {
            "client_name": client_name,
            "domain": domain,
            "tech_stack": tech_stack,
            "duration_months": duration_months,
            "team_size": team_size,
            "total_cost": total_cost,
            "upload_date": datetime.utcnow().isoformat(),
            "file_name": file.filename
        }

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "chunk_id": f"{document_id}_{idx}",
                    "chunk": chunk,
                    "metadata": json.dumps(metadata),
                    "document_type": "past_proposal"
                }
            ))

        client.upsert(
            collection_name=PAST_PROPOSALS_COLLECTION,
            points=points
        )

        logger.info(f"✅ Stored {len(points)} vectors in {PAST_PROPOSALS_COLLECTION}")

        return {
            "status": "success",
            "document_id": document_id,
            "message": f"Successfully processed and embedded SOW for {client_name} ({len(points)} vectors)."
        }

    except Exception as e:
        logger.error(f"Error processing SOW: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
