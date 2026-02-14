#!/usr/bin/env python3
"""
Script to view and explore Qdrant vector database data.
"""
import sys
import json
from qdrant_client import QdrantClient
from app.config.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, CASE_STUDY_COLLECTION

def main():
    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # List all collections
    print("\n" + "="*60)
    print("COLLECTIONS")
    print("="*60)
    collections = client.get_collections()
    for col in collections.collections:
        print(f"\n📦 Collection: {col.name}")
        
        # Get collection info
        info = client.get_collection(col.name)
        print(f"   Vectors count: {info.points_count}")
        print(f"   Vector size: {info.config.params.vectors.size}")
        print(f"   Distance: {info.config.params.vectors.distance}")
        
        # Get sample points
        print(f"\n   Sample points (first 5):")
        try:
            result = client.scroll(
                collection_name=col.name,
                limit=5,
                with_payload=True,
                with_vectors=False
            )
            points, _ = result
            
            for i, point in enumerate(points, 1):
                print(f"\n   Point {i}:")
                print(f"      ID: {point.id}")
                if point.payload:
                    print(f"      Payload keys: {list(point.payload.keys())}")
                    # Print some payload content
                    for key, value in point.payload.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"      {key}: {value[:100]}...")
                        else:
                            print(f"      {key}: {value}")
        except Exception as e:
            print(f"   ⚠️ Could not retrieve points: {e}")
    
    # Detailed view of specific collections
    print("\n" + "="*60)
    print("KNOWLEDGE BASE COLLECTION DETAILS")
    print("="*60)
    
    try:
        kb_info = client.get_collection(QDRANT_COLLECTION)
        print(f"\nCollection: {QDRANT_COLLECTION}")
        print(f"Total points: {kb_info.points_count}")
        
        # Get all points (paginated)
        print("\nAll KB documents:")
        offset = None
        page = 1
        while True:
            result = client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=10,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            points, next_offset = result
            
            if not points:
                break
                
            print(f"\n--- Page {page} ---")
            for point in points:
                print(f"\nID: {point.id}")
                if point.payload:
                    # Show document info
                    doc_name = point.payload.get('document_name', 'Unknown')
                    chunk_text = point.payload.get('text', '')
                    print(f"Document: {doc_name}")
                    print(f"Text preview: {chunk_text[:200]}...")
            
            if next_offset is None:
                break
            offset = next_offset
            page += 1
            
    except Exception as e:
        print(f"⚠️ Could not access {QDRANT_COLLECTION}: {e}")
    
    # Case studies collection
    print("\n" + "="*60)
    print("CASE STUDIES COLLECTION DETAILS")
    print("="*60)
    
    try:
        cs_info = client.get_collection(CASE_STUDY_COLLECTION)
        print(f"\nCollection: {CASE_STUDY_COLLECTION}")
        print(f"Total points: {cs_info.points_count}")
        
        # Get sample case studies
        result = client.scroll(
            collection_name=CASE_STUDY_COLLECTION,
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        points, _ = result
        
        print("\nCase studies:")
        for point in points:
            print(f"\nID: {point.id}")
            if point.payload:
                title = point.payload.get('title', 'Unknown')
                domain = point.payload.get('domain', 'Unknown')
                print(f"Title: {title}")
                print(f"Domain: {domain}")
                
    except Exception as e:
        print(f"⚠️ Could not access {CASE_STUDY_COLLECTION}: {e}")
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)

if __name__ == "__main__":
    main()
