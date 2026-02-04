#!/usr/bin/env python3
"""
Debug script for Presenton integration issues
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, '/home/sigmoid/Enhancement-Project-Scoping-Bot-2-karan/backend')

async def main():
    print("🔍 Presenton Integration Diagnostics\n")
    
    # 1. Check database connection
    print("1️⃣ Checking database connection...")
    try:
        from app.config.database import async_engine
        from sqlalchemy import text
        
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM projects"))
            count = result.scalar()
            print(f"   ✅ Database connected: {count} projects found\n")
    except Exception as e:
        print(f"   ❌ Database error: {e}\n")
        return
    
    # 2. Check for finalized scopes
    print("2️⃣ Checking for finalized scopes...")
    try:
        from app.config.database import get_async_session
        from app import models
        from sqlalchemy import select
        
        async for db in get_async_session():
            result = await db.execute(
                select(models.ProjectFile).filter(
                    models.ProjectFile.file_name == "finalized_scope.json"
                )
            )
            scopes = result.scalars().all()
            print(f"   ✅ Found {len(scopes)} finalized scopes")
            
            if scopes:
                for scope in scopes[:3]:
                    print(f"      - Project ID: {scope.project_id}")
            else:
                print("   ⚠️  No finalized scopes found!")
                print("      You need to finalize a project scope first.\n")
            break
    except Exception as e:
        print(f"   ❌ Error checking scopes: {e}\n")
        return
    
    # 3. Check Presenton container
    print("\n3️⃣ Checking Presenton container...")
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=scopebot-presenton", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        if "Up" in result.stdout:
            print(f"   ✅ Presenton container is running: {result.stdout.strip()}")
        else:
            print(f"   ❌ Presenton container not running")
            return
    except Exception as e:
        print(f"   ❌ Error checking container: {e}\n")
        return
    
    # 4. Test Presenton API
    print("\n4️⃣ Testing Presenton API...")
    try:
        result = subprocess.run(
            ["docker", "exec", "scopebot-presenton", "curl", "-s", "http://localhost:8000/api/v1/ppt/template-management/summary"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and "success" in result.stdout:
            print("   ✅ Presenton API is responding")
        else:
            print(f"   ❌ Presenton API error: {result.stdout[:200]}")
    except Exception as e:
        print(f"   ❌ Error testing API: {e}\n")
    
    print("\n✅ Diagnostics complete!")
    print("\n📝 Next steps:")
    print("   1. Make sure you have finalized a project scope")
    print("   2. Try generating presentation from the dashboard")
    print("   3. Check backend logs for detailed errors")

if __name__ == "__main__":
    asyncio.run(main())
