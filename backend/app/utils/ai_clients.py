from __future__ import annotations
import logging
import os
import time
from functools import lru_cache
from typing import List, Dict, Any

from openai import AzureOpenAI, AsyncAzureOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config.config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    CASE_STUDY_COLLECTION,
    VECTOR_DIM,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

__all__ = [
    "get_llm_client",
    "get_embed_client",
    "embed_text_ollama",  # Kept for backward compatibility
    "embed_text_azure",
    "get_qdrant_client",
]

# -------------------------------------------------------------------------
# Azure OpenAI Clients
# -------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_azure_client() -> AzureOpenAI:
    """Return synchronous Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )

@lru_cache(maxsize=1)
def get_async_azure_client() -> AsyncAzureOpenAI:
    """Return asynchronous Azure OpenAI client."""
    return AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )

def get_llm_client() -> dict:
    """
    Deprecated: Returns config dict for compatibility.
    Prefer using get_azure_client() directly.
    """
    return {
        "type": "azure",
        "endpoint": AZURE_OPENAI_ENDPOINT,
        "deployment": AZURE_OPENAI_DEPLOYMENT,
        "model": AZURE_OPENAI_DEPLOYMENT # Alias
    }

def get_embed_client() -> dict:
    return {
        "type": "azure",
        "endpoint": AZURE_OPENAI_ENDPOINT,
        "deployment": AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        "vector_dim": VECTOR_DIM
    }

# -------------------------------------------------------------------------
# Embedding generator
# -------------------------------------------------------------------------
def embed_text_azure(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using Azure OpenAI.
    """
    if not isinstance(texts, list):
        texts = [str(texts)]
    
    # Filter empty texts
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return []

    try:
        client = get_azure_client()
        # Azure OpenAI embedding call
        response = client.embeddings.create(
            input=texts,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"❌ Azure embedding failed: {e}")
        return []

# Alias for backward compatibility
embed_text_ollama = embed_text_azure

# -------------------------------------------------------------------------
# Qdrant Client
# -------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Initialize or reuse a Qdrant client (auto-creates collections if missing)."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        collections = client.get_collections().collections
        existing = [c.name for c in collections]

        # Create Knowledge Base collection
        if QDRANT_COLLECTION not in existing:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"✅ Created Qdrant collection '{QDRANT_COLLECTION}' ({VECTOR_DIM} dims)")
        
        # Create Case Study collection
        if CASE_STUDY_COLLECTION not in existing:
            client.create_collection(
                collection_name=CASE_STUDY_COLLECTION,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"✅ Created Qdrant collection '{CASE_STUDY_COLLECTION}' ({VECTOR_DIM} dims)")

        return client

    except Exception as e:
        logger.exception(f"❌ Failed to initialize Qdrant client: {e}")
        raise