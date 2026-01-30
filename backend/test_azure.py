import sys
import os
import asyncio
import logging

# Add backend to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.utils.azure_blob import upload_bytes, blob_exists, delete_blob_async

async def test_azure():
    print("🧪 Testing Azure Blob Storage Connection...")
    
    test_blob = "debug/test_connection.txt"
    test_content = b"Hello verify Azure Blob Connectivity"
    
    try:
        # 1. Upload
        print(f"   ⬆️ Uploading to {test_blob}...")
        url = await upload_bytes(test_content, test_blob)
        print(f"   ✅ Upload success: {url}")
        
        # 2. Check Exists
        print(f"   🔍 Checking existence...")
        exists = await blob_exists(test_blob)
        if exists:
            print(f"   ✅ Blob exists confirmed.")
        else:
            print(f"   ❌ Blob not found after upload!")
            
        # 3. Clean up
        print(f"   🗑️ Cleaning up...")
        deleted = await delete_blob_async(test_blob)
        if deleted:
            print(f"   ✅ Cleanup success.")
        else:
            print(f"   ⚠️ Cleanup returned False (maybe already gone).")
            
    except Exception as e:
        print(f"   ❌ Azure Test FAILED: {type(e).__name__}: {e}")
        print("   -> Please check AZURE_STORAGE_KEY in .env")

if __name__ == "__main__":
    asyncio.run(test_azure())
