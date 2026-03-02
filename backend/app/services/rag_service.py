
import logging
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.utils.ai_clients import embed_text_ollama, get_qdrant_client
from app.config.config import QDRANT_COLLECTION, CASE_STUDY_COLLECTION
from qdrant_client import models as models_qdrant

logger = logging.getLogger(__name__)

async def vectorize_text(text: str, metadata: Dict[str, Any]) -> None:
    """
    Vectorizes the provided text and stores it in Qdrant with metadata.
    """
    if not text:
        logger.warning("⚠️ No text to vectorize.")
        return

    try:
        qdrant_client = get_qdrant_client()
        
        # 1. Chunking (Simple chunking for now)
        chunks = _chunk_text(text)
        
        # 2. Embedding
        embeddings = embed_text_ollama(chunks)
        
        if not embeddings or len(embeddings) != len(chunks):
            raise ValueError("Failed to generate embeddings")

        # 3. Store in Qdrant
        points = []
        doc_id = metadata.get("document_id", str(uuid.uuid4()))
        
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            # Stable integer ID
            point_id_str = f"{doc_id}_{idx}"
            point_id = int(hashlib.sha256(point_id_str.encode()).hexdigest()[:16], 16)
            
            payload = metadata.copy()
            payload.update({
                "content": chunk[:1500],
                "chunk_index": idx,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            points.append(
                models_qdrant.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        # Decide collection
        collection_name = QDRANT_COLLECTION
        if metadata.get("type") == "case_study" or metadata.get("document_type") == "case_study":
             collection_name = CASE_STUDY_COLLECTION

        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        logger.info(f"✅ Successfully vectorized {len(points)} chunks into {collection_name}")

    except Exception as e:
        logger.error(f"❌ Error in vectorize_text: {e}")
        raise e

def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Helper to split text into chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks
