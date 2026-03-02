import json

draft = {
  "activities": [
    {"ID": 1, "Activities": "Dev", "Start Date": "2025-01-01", "End Date": "2025-01-30", "Effort Months": 1.0},
    {"ID": 2, "Activities": "Deploy", "Start Date": "2025-02-01", "End Date": "2025-02-15", "Effort Months": 0.5}
  ]
}

print("Prompt rules read:")
print("1. Identify logical chronological position.")
print("2. Insert it exactly there.")
print("3. CRITICAL MATHEMATICAL STEP: Shift subsequent dates.")
