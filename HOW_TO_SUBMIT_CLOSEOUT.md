# How to Submit Project Closeout Data (User Guide)

## Good News! 🎉
Your application **already has a built-in closeout form**! You don't need to use the API manually.

## Step-by-Step Instructions

### 1. Navigate to a Project
- Go to your **Dashboard** (`http://localhost:5173/dashboard`)
- Click on any project in the "Recent Projects" table
- Or go to **Projects** → Select a project

### 2. Finalize the Project Scope First
Before you can close a project, it needs to have a finalized scope:
- Click **"Regenerate Scope"** if you haven't already
- Review and finalize the scope in the Exports page
- Return to the Project Details page

### 3. Click "Close Project"
- On the Project Details page, look for the green **"Close Project"** button (top right)
- Click it to open the closeout form modal

### 4. Fill in Actual Data
The form will show a table with all project activities:

| Activity | Est. Months | Actual Months | Notes |
|----------|-------------|---------------|-------|
| Backend Development | 2 months | **[Enter here]** | **[Why different?]** |
| Frontend Development | 1.5 months | **[Enter here]** | **[Why different?]** |
| Testing | 0.5 months | **[Enter here]** | **[Why different?]** |

**For each activity:**
- **Actual Months**: Enter how long it actually took (e.g., `2.5` for 2.5 months)
- **Notes**: Explain why it differed from the estimate (e.g., "API integration was more complex than expected")

### 5. Submit the Form
- Click **"Save & Learn"** button at the bottom
- The system will:
  - Store the actual data
  - Calculate accuracy metrics
  - Update the Accuracy Dashboard
  - Improve future estimates based on this learning

### 6. View Results in Accuracy Dashboard
- Navigate to **Accuracy Dashboard** (purple button on main dashboard)
- Or go directly to `http://localhost:5173/accuracy`
- You should now see:
  - ✅ Non-zero accuracy percentages
  - ✅ Your project in the breakdown table
  - ✅ Real metrics instead of 0%

## Example Closeout

Here's an example of how to fill out the form:

**Project:** E-commerce Platform

| Activity | Estimated | Actual | Notes |
|----------|-----------|--------|-------|
| Backend API | 2 months | 2.5 months | Third-party payment gateway integration took longer |
| Frontend | 1.5 months | 1.2 months | Reused components from previous project |
| Database | 1 month | 1.1 months | Additional indexes needed for performance |
| Testing | 0.5 months | 0.8 months | More edge cases discovered during QA |

## Tips

✅ **Be Honest**: Accurate data helps the AI learn and improve future estimates

✅ **Add Context**: Use the Notes field to explain variances - this helps the AI understand patterns

✅ **Close Projects Regularly**: The more closeout data you provide, the more accurate future estimates become

✅ **Check Accuracy Dashboard**: Monitor how your estimation accuracy improves over time

## Troubleshooting

**Q: "Close Project" button is disabled or missing?**
- Make sure the project has a finalized scope first
- Regenerate and finalize the scope if needed

**Q: Form shows no activities?**
- The project needs to have activities in the finalized scope
- Go to Exports page and ensure scope is finalized

**Q: Data not showing in Accuracy Dashboard?**
- Refresh the Accuracy Dashboard page
- Check that the closeout was submitted successfully (you should see a success message)

**Q: Want to update closeout data?**
- Currently, you can only submit closeout data once per project
- Make sure your data is accurate before submitting

## What Happens Behind the Scenes

When you submit closeout data:

1. **Data Storage**: Actual vs estimated data is stored in the knowledge base
2. **Accuracy Calculation**: System calculates:
   - Duration accuracy = `1 - (|actual - estimated| / actual)`
   - Overall accuracy = average across all metrics
3. **Continuous Learning**: The AI uses this data to improve future project estimates
4. **Dashboard Update**: Accuracy Dashboard automatically reflects the new data

## Next Steps

After submitting closeout data for multiple projects:
- Monitor trends in the Accuracy Dashboard
- Identify patterns (e.g., "Backend always takes 20% longer")
- Use insights to improve project planning
- Watch estimation accuracy improve over time!
