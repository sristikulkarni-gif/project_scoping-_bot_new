import asyncio
from app.utils import azure_blob

PROJECT_ID = "ecf43b71-c27f-4bd2-8539-a0e76b8114bd"
SVG_FILENAME = f"architecture_{PROJECT_ID}.svg"
BLOB_PATH = f"projects/{PROJECT_ID}/{SVG_FILENAME}"

async def inspect():
    print(f"Downloading {BLOB_PATH}...")
    try:
        data = await azure_blob.download_bytes(BLOB_PATH)
        print(f"Downloaded {len(data)} bytes")
        content = data.decode('utf-8')
        print("--- SVG Header ---")
        print(content[:500])
        print("------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
