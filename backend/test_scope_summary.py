
import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Load env
load_dotenv(".env")

# Mock things to avoid full app load
class MockProject:
    name = "Test E-Commerce App"
    domain = "E-Commerce"
    complexity = "Medium"
    tech_stack = "React, Python, PostgreSQL"
    use_cases = "User login, Product search, Cart, Checkout"
    compliance = "GDPR"
    duration = "3"

from app.utils.scope_engine import _build_scope_prompt, ollama_chat

async def test_generation():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    print("🚀 Building Prompt...")
    rfp_text = "I want to build an e-commerce platform for selling organic food."
    kb_chunks = []
    project = MockProject()
    
    # Passing a user override to test that too
    questions_context = "User: Change Frontend to 5 months.\nAssistant: Okay."
    
    prompt = _build_scope_prompt(rfp_text, kb_chunks, project, questions_context=questions_context)
    
    print("🚀 Calling Azure OpenAI...")
    try:
        response_json_str = await asyncio.to_thread(
            lambda: ollama_chat(prompt, format_json=True)
        )
        
        print("\n✅ Response Received:")
        print(response_json_str[:500] + "...")
        
        # Check for summary
        if '"project_summary"' in response_json_str:
            print("\n🎉 SUCCESS: 'project_summary' found in response!")
        else:
            print("\n❌ FAILURE: 'project_summary' MISSING in response.")
            
        # Check for override
        if '"Effort Months": 5.0' in response_json_str or '"Effort Months": 5' in response_json_str:
             print("\n🎉 SUCCESS: User override (5 months) found!")
        else:
             print("\n⚠️ WARNING: User override (5 months) might be missing (check full output).")
             
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_generation())
