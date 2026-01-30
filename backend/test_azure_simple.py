
import sys
import os
import asyncio

# Fix path to allow imports from app
sys.path.append(os.getcwd())

from app.utils.ai_clients import embed_text_azure, get_azure_client
from app.config.config import AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_EMBEDDING_DEPLOYMENT

def test_azure():
    print(f"Testing Azure OpenAI Connection...")
    print(f"Deployment: {AZURE_OPENAI_DEPLOYMENT}")
    print(f"Embedding Deployment: {AZURE_OPENAI_EMBEDDING_DEPLOYMENT}")

    # Test Embedding
    try:
        print("\n1. Testing Embeddings...")
        text = "Hello Azure OpenAI"
        embeddings = embed_text_azure([text])
        if embeddings:
            dim = len(embeddings[0])
            print(f"✅ Success! Embedding dimension: {dim}")
        else:
            print("❌ Embedding returned empty list")
    except Exception as e:
        print(f"❌ Embedding Failed: {e}")

    # Test Chat Completion
    try:
        print("\n2. Testing Chat Completion...")
        client = get_azure_client()
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=10
        )
        content = response.choices[0].message.content
        print(f"✅ Success! Response: {content}")
    except Exception as e:
        print(f"❌ Chat Completion Failed: {e}")

if __name__ == "__main__":
    test_azure()
