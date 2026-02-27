import asyncio
import os
import uuid
from app.config.database import AsyncSessionLocal
from app.utils.ai_clients import get_qdrant_client, embed_text_azure
from qdrant_client.models import PointStruct
import json

from app.utils.scope_engine import _retrieve_past_proposals

async def test_sow_upload_and_retrieval():
    print("Testing SOW Upload & Retrieval RAG...")
    
    PAST_PROPOSALS_COLLECTION = os.getenv("PAST_PROPOSALS_COLLECTION", "past_proposals")
    client = get_qdrant_client()
    
    # 1. Create a fake SOW chunk
    print("\n--- 1. Creating Fake Past Proposal ---")
    fake_sow_text = "This is a past proposal for a massive CRM migration. Phase 1 took 3 months, Phase 2 took 6 months. It was a 9-month project for Salesforce integration with 12 developers."
    
    chunks = [fake_sow_text]
    embeddings = embed_text_azure(chunks)
    
    metadata = {
        "client_name": "Acme Corp",
        "domain": "CRM",
        "tech_stack": "Salesforce",
        "duration_months": 9.0,
        "team_size": 12,
        "total_cost": 850000.0,
        "file_name": "acme_crm_sow.pdf"
    }

    document_id = str(uuid.uuid4())
    point_id = str(uuid.uuid4())
    
    client.upsert(
        collection_name=PAST_PROPOSALS_COLLECTION,
        points=[PointStruct(
            id=point_id,
            vector=embeddings[0],
            payload={
                "document_id": document_id,
                "chunk": fake_sow_text,
                "metadata": json.dumps(metadata),
                "document_type": "past_proposal"
            }
        )]
    )
    print(f"Inserted into Qdrant collection: {PAST_PROPOSALS_COLLECTION}.")
    
    # 2. Test Retrieval
    print("\n--- 2. Testing Retrieval ---")
    fake_rfp = "We are looking for a vendor to help us migrate to a new CRM system. We need to integrate Salesforce across all branches."
    
    results = _retrieve_past_proposals(fake_rfp, k=1)
    
    if results:
        res = results[0]
        print(f"✅ RAG Retrieval matched: {res['client_name']} ({res['domain']})")
        print(f"   Duration: {res['duration_months']} months")
        print(f"   Cost: ${res['total_cost']:,.0f}")
        print(f"   Summary text: {res['summary'][:100]}...")
    else:
        print("❌ RAG Retrieval failed to find the document.")
        
    print("\nTest finished.")

if __name__ == "__main__":
    asyncio.run(test_sow_upload_and_retrieval())
