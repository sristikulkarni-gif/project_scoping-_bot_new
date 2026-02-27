import asyncio
import sys
import logging
from app.utils.presenton_client import presenton_client

logging.basicConfig(level=logging.INFO)

async def test_generation():
    dummy_scope = {
        "overview": {
            "Project Name": "Alpha Migration Engine",
            "Description": "A tool to migrate legacy database environments to cloud-native solutions.",
            "Domain": "Cloud Infrastructure",
            "Tech Stack": "Python, React, AWS",
            "Complexity": "High",
            "Duration": "6 Months"
        },
        "executive_summary": "This project delivers a seamless cloud migration path for enterprise clients, minimizing downtime and ensuring zero data loss during transitions.",
        "objectives": [
            "Reduce migration time by 40%",
            "Ensure 99.99% uptime during switchover",
            "Automate schema translation"
        ],
        "activities": [
            {
                "Activities": "Phase 1: Discovery",
                "Deliverable": "Architecture mapping and risk assessment report.",
                "Effort": "1"
            },
            {
                "Activities": "Phase 2: Alpha Build",
                "Deliverable": "Core engine development and ETL pipeline.",
                "Effort": "2.5"
            },
            {
                "Activities": "Phase 3: UAT & Testing",
                "Deliverable": "Load testing and user acceptance criteria signoff.",
                "Effort": "1.5"
            },
            {
                "Activities": "Phase 4: Deployment",
                "Deliverable": "Production rollout and monitoring setup.",
                "Effort": "1"
            }
        ],
        "resourcing_plan": [
            {"Resources": "Solutions Architect", "Effort": "6"},
            {"Resources": "Lead Data Engineer", "Effort": "6"},
            {"Resources": "Backend Dev 1", "Effort": "4"},
            {"Resources": "Backend Dev 2", "Effort": "4"},
            {"Resources": "QA Engineer", "Effort": "3"}
        ],
        "total_cost": 245000.00
    }
    
    print("Testing Deterministic PPT Generation...")
    try:
        result = await presenton_client.generate_presentation(dummy_scope, n_slides=10, template="standard")
        print("\nSUCCESS!")
        print("Response:", result)
    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_generation())
