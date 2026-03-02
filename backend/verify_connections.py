
import asyncio
import os
import sys
from app.config.config import OLLAMA_HOST, OLLAMA_EMBED_MODEL, QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
from app.utils.ai_clients import embed_text_ollama, get_qdrant_client

def test_ollama():
    print(f"--- Testing Ollama ({OLLAMA_HOST}) ---")
    text = "Testing embedding generation"
    try:
        print(f"Generating embedding for: '{text}' using model '{OLLAMA_EMBED_MODEL}'...")
        embeddings = embed_text_ollama([text])
        if embeddings and len(embeddings) > 0:
            print(f"✅ Success! Embedding length: {len(embeddings[0])}")
        else:
            print("❌ Failed: No embeddings returned")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_qdrant():
    print(f"\n--- Testing Qdrant ({QDRANT_HOST}:{QDRANT_PORT}) ---")
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        names = [c.name for c in collections]
        print(f"✅ Connected to Qdrant. Collections: {names}")
        
        if QDRANT_COLLECTION in names:
            print(f"✅ Collection '{QDRANT_COLLECTION}' exists.")
        else:
            print(f"⚠️ Collection '{QDRANT_COLLECTION}' NOT found. It should have been created by get_qdrant_client.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Ensure we can import app
    sys.path.append(os.getcwd())
    
    test_ollama()
    test_qdrant()
