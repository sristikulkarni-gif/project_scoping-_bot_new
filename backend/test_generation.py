import sys
import os
import time

# Add backend to path
sys.path.append(os.getcwd())

from app.utils.scope_engine import ollama_chat

def test_generation():
    print("🧪 Testing Ollama Generation with Parameters...")
    
    # Simulate a reasonable context length
    prompt = "This is a test prompt. " * 50  # ~250 tokens
    prompt += "\n\nPlease generate a JSON response with 3 items under 'questions'."
    
    print(f"   📤 Sending prompt ({len(prompt)} chars)...")
    start = time.time()
    
    try:
        response = ollama_chat(prompt, format_json=False) # format_json=False is used in scope_engine for questions
        duration = time.time() - start
        
        if response:
            print(f"   ✅ Generation Success in {duration:.2f}s")
            print(f"   📝 Response preview: {response[:100]}...")
        else:
            print(f"   ❌ Generation returned empty string.")
            
    except Exception as e:
        print(f"   ❌ Generation FAILED: {e}")

if __name__ == "__main__":
    test_generation()
