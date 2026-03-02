#!/usr/bin/env python3
"""
Run database migration for resource-level closeout
"""
import asyncio
from sqlalchemy import text
from app.config.database import async_engine

async def run_migration():
    """Apply migration to add project status and resource actuals"""
    
    migrations = [
        # 1. Add status column
        """ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft' NOT NULL""",
        
        # 2. Add closed_at column
        """ALTER TABLE projects ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP WITH TIME ZONE""",
        
        # 3. Add actual_total_cost column
        """ALTER TABLE projects ADD COLUMN IF NOT EXISTS actual_total_cost FLOAT""",
        
        # 4. Create index on status
        """CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)""",
        
        # 5. Create resource_actuals table
        """CREATE TABLE IF NOT EXISTS resource_actuals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            resource_name VARCHAR(100) NOT NULL,
            rate_per_month FLOAT NOT NULL,
            estimated_effort_months FLOAT NOT NULL,
            actual_effort_months FLOAT NOT NULL,
            estimated_cost FLOAT NOT NULL,
            actual_cost FLOAT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )""",
        
        # 6. Create index on project_id
        """CREATE INDEX IF NOT EXISTS idx_resource_actuals_project_id ON resource_actuals(project_id)""",
        
        # 7. Create index on created_at
        """CREATE INDEX IF NOT EXISTS idx_resource_actuals_created_at ON resource_actuals(created_at)""",
        
        # 8. Update existing projects
        """UPDATE projects SET status = 'draft' WHERE status IS NULL"""
    ]
    
    print("🔄 Running migration...")
    
    try:
        async with async_engine.begin() as conn:
            for i, sql in enumerate(migrations, 1):
                print(f"  [{i}/{len(migrations)}] Executing...")
                await conn.execute(text(sql))
                
        print("✅ Migration completed successfully!")
        print("\nChanges applied:")
        print("  - Added 'status', 'closed_at', 'actual_total_cost' to projects table")
        print("  - Created 'resource_actuals' table")
        print("  - Created indexes for performance")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
