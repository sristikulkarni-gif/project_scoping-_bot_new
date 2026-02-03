
import sys
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Setup path
sys.path.append(os.getcwd())

from app.config.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, CASE_STUDY_COLLECTION, VECTOR_DIM

def recreate_collections():
    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    collections = [QDRANT_COLLECTION, CASE_STUDY_COLLECTION]
    
    for col_name in collections:
        print(f"Checking collection '{col_name}'...")
        try:
            client.delete_collection(col_name)
            print(f"🗑️ Deleted existing collection '{col_name}' (old dimensions).")
        except Exception as e:
            print(f"ℹ️ Collection '{col_name}' likely didn't exist or error: {e}")
            
        print(f"Creating '{col_name}' with dimension {VECTOR_DIM}...")
        client.create_collection(
            collection_name=col_name,
            vectors_config=models.VectorParams(
                size=VECTOR_DIM,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"✅ Created '{col_name}' successfully.")

if __name__ == "__main__":
    recreate_collections()
