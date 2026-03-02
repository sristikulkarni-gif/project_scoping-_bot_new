from __future__ import annotations
import logging
import os
import time
from functools import lru_cache
from typing import List, Dict, Any
import httpx

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

# Timeout configuration: 60s total for LLM calls, 10s connect
_AZURE_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

__all__ = [
    "get_llm_client",
    "get_embed_client",
    "embed_text_ollama",  # Kept for backward compatibility
    "embed_text_azure",
    "get_qdrant_client",
]

# -------------------------------------------------------------------------
# Azure OpenAI Clients (Module-level singletons, always created with timeout)
# -------------------------------------------------------------------------
_sync_client: AzureOpenAI | None = None
_async_client: AsyncAzureOpenAI | None = None

def get_azure_client() -> AzureOpenAI:
    """Return synchronous Azure OpenAI client with explicit timeout."""
    global _sync_client
    if _sync_client is None:
        _sync_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            timeout=_AZURE_TIMEOUT,
        )
    return _sync_client

def get_async_azure_client() -> AsyncAzureOpenAI:
    """Return asynchronous Azure OpenAI client with explicit timeout."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            timeout=_AZURE_TIMEOUT,
        )
    return _async_client

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

# -------------------------------------------------------------------------
# Embedding generator
# -------------------------------------------------------------------------
def embed_text_azure(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using Azure OpenAI.
    Automatically truncates texts to stay within the 8192-token model limit.
    """
    if not isinstance(texts, list):
        texts = [str(texts)]
    
    # Filter empty texts
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return []

    # Truncate each text to stay within Azure embedding model's 8192-token limit
    # We use a character-based approximation (1 token ≈ 4 chars) with a safe cap.
    # Using tiktoken would be more precise but adds latency; char cap is safer and fast.
    MAX_EMBEDDING_TOKENS = 8000  # slightly under 8192 for safety margin
    MAX_CHARS = MAX_EMBEDDING_TOKENS * 4  # ~32000 chars
    truncated_texts = []
    for text in texts:
        if len(text) > MAX_CHARS:
            logger.warning(
                f"⚠️ Text too long for embedding ({len(text)} chars). "
                f"Truncating to {MAX_CHARS} chars (~{MAX_EMBEDDING_TOKENS} tokens)."
            )
            text = text[:MAX_CHARS]
        truncated_texts.append(text)

    try:
        client = get_azure_client()
        # Azure OpenAI embedding call
        response = client.embeddings.create(
            input=truncated_texts,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"❌ Azure embedding failed: {e}")
        return []

# Alias: Use Azure for everything now
embed_text_ollama = embed_text_azure


def ollama_chat(prompt: str, model: str = None, temperature: float = 0.7, format_json: bool = False) -> str:
    """
    Generate text using Azure OpenAI (replaces Ollama).
    Arguments 'model' and 'format_json' are adapted for Azure.
    """
    try:
        client = get_azure_client()
        
        # Azure OpenAI Chat Completion
        messages = [{"role": "user", "content": prompt}]
        if format_json:
            # Add system instruction for JSON if needed, or rely on prompt
            messages.insert(0, {"role": "system", "content": "You are a helpful AI. Please respond in valid JSON format."})
            
        logger.info(f"🚀 Calling Azure OpenAI (Model: {AZURE_OPENAI_DEPLOYMENT})...")
        
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT, # Use deployment from config
            messages=messages,
            temperature=temperature,
            max_tokens=16384, # Large enough for scope generation
            response_format={"type": "json_object"} if format_json else None
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f" Azure OpenAI Chat failed: {e}")
        return ""



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

        # Create Past Proposals collection
        PAST_PROPOSALS_COLLECTION = os.getenv("PAST_PROPOSALS_COLLECTION", "past_proposals")
        if PAST_PROPOSALS_COLLECTION not in existing:
            client.create_collection(
                collection_name=PAST_PROPOSALS_COLLECTION,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"✅ Created Qdrant collection '{PAST_PROPOSALS_COLLECTION}' ({VECTOR_DIM} dims)")

        return client

    except Exception as e:
        logger.exception(f"❌ Failed to initialize Qdrant client: {e}")
        raise