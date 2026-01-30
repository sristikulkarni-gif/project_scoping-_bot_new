import sys
import os
import logging

# Add backend to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("app.utils.ai_clients").setLevel(logging.INFO)

from app.utils.ai_clients import embed_text_ollama

def test_long_embedding():
    print("🧪 Testing Long Text Embedding...")
    
    # Create a long text (Ollama/Nomic might have limit)
    # Nomic has 8192 context usually, but let's test.
    long_text = "word " * 5000 
    
    print(f"   📤 Sending text of length {len(long_text)}...")
    try:
        vecs = embed_text_ollama([long_text])
        if vecs:
            print(f"   ✅ Success. Vector dim: {len(vecs[0])}")
        else:
            print("   ❌ Failed (empty return)")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_long_embedding()
