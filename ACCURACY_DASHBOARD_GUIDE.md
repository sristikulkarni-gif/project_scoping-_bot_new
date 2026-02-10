# How to Provide Data to the Accuracy Dashboard

## Overview
The Accuracy Dashboard needs **Project Closeout Data** to calculate accuracy metrics. This data compares your **estimated** project scope with **actual** results.

## Method 1: Using the Project Details Page (Recommended)

1. **Navigate to a completed project:**
   - Go to Dashboard → Click on any project
   - Or go to `http://localhost:5173/projects/{project_id}`

2. **Look for the "Close Project" or "Submit Closeout" button**
   - This should be on the project details page
   - Click it to open the closeout form

3. **Fill in the actual data:**
   - For each activity, enter the **actual duration** vs the estimated
   - Add any notes about variances
   - Submit the form

## Method 2: Using the API Directly

If the UI doesn't have a closeout form yet, you can submit data via API:

### Step 1: Get Your Authentication Token

Open browser console on `http://localhost:5173` and run:
```javascript
localStorage.getItem('token')
```

Copy the token value.

### Step 2: Get a Project ID

List your projects:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8000/api/projects
```

Copy a project ID from the response.

### Step 3: Submit Closeout Data

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "activities": [
      {
        "name": "Backend Development",
        "estimated_duration": "2 months",
        "actual_duration": "2.5 months",
        "notes": "API integration took longer than expected"
      },
      {
        "name": "Frontend Development",
        "estimated_duration": "1.5 months",
        "actual_duration": "1.2 months",
        "notes": "Completed ahead of schedule"
      }
    ]
  }' \
  http://localhost:8000/api/projects/YOUR_PROJECT_ID/closeout
```

## Method 3: Using Browser Console (Quick Test)

1. Open `http://localhost:5173` in your browser
2. Open Developer Tools (F12)
3. Go to Console tab
4. Run this code (replace `PROJECT_ID` with a real project ID):

```javascript
const token = localStorage.getItem('token');
const projectId = 'YOUR_PROJECT_ID_HERE';

fetch(`http://localhost:8000/api/projects/${projectId}/closeout`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    activities: [
      {
        name: "Backend Development",
        estimated_duration: "2 months",
        actual_duration: "2.5 months",
        notes: "Underestimated complexity"
      },
      {
        name: "Frontend Development",
        estimated_duration: "1.5 months",
        actual_duration: "1.3 months",
        notes: "On track"
      },
      {
        name: "Testing",
        estimated_duration: "2 weeks",
        actual_duration: "3 weeks",
        notes: "More bugs than expected"
      }
    ]
  })
})
.then(r => r.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));
```

## What Happens After Submission

1. The system stores the closeout data in the knowledge base
2. It calculates accuracy metrics:
   - Duration accuracy = `1 - (|actual - estimated| / actual)`
   - Overall accuracy = average of all metrics
3. The Accuracy Dashboard automatically updates
4. Future project scopes will be more accurate based on this learning

## Viewing the Results

1. Navigate to `http://localhost:5173/accuracy`
2. You should now see:
   - Non-zero accuracy percentages
   - Your project listed in the breakdown table
   - Trends showing improvement over time

## Example Data Format

```json
{
  "activities": [
    {
      "name": "Activity Name",
      "estimated_duration": "X months" or "Y days",
      "actual_duration": "X months" or "Y days",
      "notes": "Optional explanation of variance"
    }
  ]
}
```

## Troubleshooting

**Q: Dashboard still shows 0%?**
- Make sure you submitted closeout data successfully
- Check that the project has `has_finalized_scope = true`
- Refresh the Accuracy Dashboard page

**Q: API returns 401 Unauthorized?**
- Your token might be expired
- Log out and log back in to get a fresh token

**Q: API returns 404 Not Found?**
- Check that the project ID is correct
- Ensure the closeout endpoint exists in your backend

## Next Steps

Once you have closeout data from multiple projects, the dashboard will show:
- Trends over time
- Accuracy by complexity level
- Accuracy by domain/industry
- Areas where estimates are consistently off
