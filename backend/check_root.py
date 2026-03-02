import asyncio
from app.utils.azure_blob import container

async def check_root_access():
    print(f"Checking root success to container: {container.container_name}")
    
    # List just the first few items to confirm access
    count = 0
    folders = set()
    
    print("Listing top-level items:")
    async for blob in container.list_blobs():
        # Get the top-level folder name
        if "/" in blob.name:
            folder = blob.name.split("/")[0]
            if folder not in folders:
                print(f" 📁 Folder: {folder}/")
                folders.add(folder)
        else:
            print(f" 📄 File: {blob.name}")
            
        count += 1
        if count >= 20: # Limit output
            print("... (more files exist)")
            break
            
    if count == 0:
        print("Container is empty.")
    else:
        print(f"\nSuccessfully accessed container.")

if __name__ == "__main__":
    asyncio.run(check_root_access())
