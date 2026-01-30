import os
import sys
import logging

# Add backend to path
sys.path.append(os.getcwd())

from app.utils.ai_clients import get_azure_client, embed_text_azure
from app.config.config import AZURE_OPENAI_DEPLOYMENT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_azure_connection():
    print("🧪 Testing Azure OpenAI Connection...")
    
    # 1. Test Chat Completion
    print(f"\n1. Testing Chat Completion (Model: {AZURE_OPENAI_DEPLOYMENT})...")
    try:
        client = get_azure_client()
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=50
        )
        print(f"   ✅ Chat Success! Response: {response.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"   ❌ Chat Failed: {e}")

    # 2. Test Embeddings
    print(f"\n2. Testing Embeddings...")
    try:
        texts = ["Hello world", "Azure AI test"]
        embeddings = embed_text_azure(texts)
        if embeddings and len(embeddings) == 2:
            dim = len(embeddings[0])
            print(f"   ✅ Embedding Success! Generated 2 vectors of dimension {dim}")
        else:
            print(f"   ❌ Embedding returned invalid result: {embeddings}")
    except Exception as e:
        print(f"   ❌ Embedding Failed: {e}")

if __name__ == "__main__":
    test_azure_connection()
