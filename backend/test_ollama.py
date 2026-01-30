import sys
import os
import asyncio

# Add backend to path so we can import app modules
sys.path.append(os.getcwd())

from app.utils.ai_clients import get_llm_client, embed_text_ollama
from app.config.config import OLLAMA_HOST, OLLAMA_MODEL

def test_ollama_connection():
    print(f"Checking Ollama Configuration...")
    print(f"Host: {OLLAMA_HOST}")
    print(f"Model: {OLLAMA_MODEL}")
    
    cfg = get_llm_client()
    print(f"Client Config: {cfg}")
    
    print("\nTesting Text Embedding...")
    try:
        embeddings = embed_text_ollama(["Hello world"])
        if embeddings and len(embeddings) > 0:
            print(f"✅ Embedding Success! Vector length: {len(embeddings[0])}")
        else:
            print("❌ Embedding returned empty list")
    except Exception as e:
        print(f"❌ Embedding Failed: {e}")

    print("\nTesting Text Generation (via raw request to force check)...")
    import requests
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": "Say 'Ollama is working' and nothing else.",
            "stream": False
        }
        response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        if response.status_code == 200:
            print(f"✅ Generation Success! Response: {response.json().get('response', '').strip()}")
        else:
            print(f"❌ Generation Failed: Status {response.status_code}, Body: {response.text}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_ollama_connection()
