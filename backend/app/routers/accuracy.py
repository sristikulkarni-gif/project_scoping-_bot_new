"""
Accuracy Metrics API Endpoints

Provides endpoints for measuring and displaying application accuracy
by comparing estimated project scopes with actual outcomes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.config.database import get_async_session
from app.auth.router import fastapi_users
from app.utils.ai_clients import get_qdrant_client
from app.config.config import QDRANT_COLLECTION
import re

router = APIRouter(prefix="/api/accuracy", tags=["Accuracy Metrics"])

# Get current active user dependency
current_active_user = fastapi_users.current_user(active=True)


def _get_closeout_data_from_qdrant(project_ids: List[str]) -> dict:
    """
    Query Qdrant for closeout data for given project IDs.
    Returns a dict mapping project_id to closeout information.
    """
    if not project_ids:
        return {}
    
    try:
        qdrant_client = get_qdrant_client()
        closeout_data = {}
        
        for project_id in project_ids:
            # Query Qdrant for closeout records
            results = qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION,
                scroll_filter={
                    "must": [
                        {"key": "type", "match": {"value": "actual_data"}},
                        {"key": "project_id", "match": {"value": str(project_id)}}
                    ]
                },
                limit=10
            )
            
            if results and results[0]:
                points = results[0]
                if points:
                    # Parse the closeout text to extract actual durations
                    selected_point = None
                    
                    # First pass: look for records with Cost data (newer) AND non-zero cost if possible
                    # We prefer records that look "complete"
                    candidate_points = []
                    for point in points:
                        content = point.payload.get("content", "")
                        if "ACTUAL COST:" in content and "ACTUAL DURATION:" in content:
                            candidate_points.append(point)
                    
                    # If candidates exist, try to find one with non-zero cost
                    for p in candidate_points:
                        if "$0" not in p.payload.get("content", "") and "ACTUAL COST: $0" not in p.payload.get("content", ""):
                             selected_point = p
                             break
                    
                    # Fallback to any cost record
                    if not selected_point and candidate_points:
                        selected_point = candidate_points[0]

                    # Second pass: if no cost data found, take any valid closeout (older)
                    if not selected_point:
                        for point in points:
                            content = point.payload.get("content", "")
                            if "ACTUAL DURATION:" in content:
                                selected_point = point
                                break
                    
                    if selected_point:
                        closeout_data[str(project_id)] = {
                            "content": selected_point.payload.get("content", ""),
                            "payload": selected_point.payload
                        }
        
        return closeout_data
    except Exception as e:
        print(f"Error querying Qdrant for closeout data: {e}")
        return {}


def _calculate_accuracy_from_closeout(closeout_text: str) -> dict:
    """
    Parse closeout text and calculate accuracy metrics.
    Returns dict with duration_accuracy, cost_accuracy, and other metrics.
    """
    try:
        # Extract estimated and actual durations from the text
        estimated_durations = []
        actual_durations = []
        
        # Pattern: "Estimated Duration: X months" and "ACTUAL DURATION: Y months"
        est_pattern = r"Estimated Duration:\s*([\d.]+)\s*months?"
        act_pattern = r"ACTUAL DURATION:\s*([\d.]+)\s*months?"
        
        est_matches = re.findall(est_pattern, closeout_text, re.IGNORECASE)
        act_matches = re.findall(act_pattern, closeout_text, re.IGNORECASE)
        
        for est, act in zip(est_matches, act_matches):
            try:
                est_val = float(est)
                act_val = float(act)
                if est_val > 0 and act_val > 0:
                    estimated_durations.append(est_val)
                    actual_durations.append(act_val)
            except ValueError:
                continue
        
        # NEW: Extract estimated and actual costs
        est_cost_pattern = r"Estimated Cost:\s*\$?([\d,]+\.?\d*)"
        act_cost_pattern = r"ACTUAL COST:\s*\$?([\d,]+\.?\d*)"
        
        est_cost_matches = re.findall(est_cost_pattern, closeout_text, re.IGNORECASE)
        act_cost_matches = re.findall(act_cost_pattern, closeout_text, re.IGNORECASE)
        
        estimated_costs = []
        actual_costs = []
        
        for est, act in zip(est_cost_matches, act_cost_matches):
            try:
                est_val = float(est.replace(',', ''))
                act_val = float(act.replace(',', ''))
                
                # Relaxed condition: Include if Actual > 0, even if Estimate is 0 (unplanned cost)
                # Or if both are > 0 (normal case)
                if act_val > 0 or (est_val > 0 and act_val >= 0):
                    estimated_costs.append(est_val)
                    actual_costs.append(act_val)
            except ValueError:
                continue
        
        # Calculate duration accuracy
        duration_accuracies = []
        duration_variances = []
        for est, act in zip(estimated_durations, actual_durations):
            variance = abs(act - est) / est * 100 if est > 0 else 0
            accuracy = max(0, 100 - variance)
            duration_accuracies.append(accuracy)
            duration_variances.append(variance)
        
        # Calculate cost accuracy
        cost_accuracies = []
        cost_variances = []
        for est, act in zip(estimated_costs, actual_costs):
            if est > 0:
                variance = abs(act - est) / est * 100
                accuracy = max(0, 100 - variance)
            else:
                # Est is 0, but Act > 0 -> Infinite variance, 0% accuracy
                variance = 100.0  # Cap variance for reporting
                accuracy = 0.0
            
            cost_accuracies.append(accuracy)
            cost_variances.append(variance)
        
        avg_duration_accuracy = sum(duration_accuracies) / len(duration_accuracies) if duration_accuracies else 0
        avg_duration_variance = sum(duration_variances) / len(duration_variances) if duration_variances else 0
        
        avg_cost_accuracy = sum(cost_accuracies) / len(cost_accuracies) if cost_accuracies else 0
        avg_cost_variance = sum(cost_variances) / len(cost_variances) if cost_variances else 0
        
        return {
            "duration_accuracy": round(avg_duration_accuracy, 1),
            "duration_variance": round(avg_duration_variance, 1),
            "cost_accuracy": round(avg_cost_accuracy, 1),
            "cost_variance": round(avg_cost_variance, 1),
            "activities_count": len(duration_accuracies),
            "cost_data_points": len(cost_accuracies),
            "total_estimated_cost": sum(estimated_costs) if estimated_costs else 0,
            "total_actual_cost": sum(actual_costs) if actual_costs else 0
        }
    except Exception as e:
        print(f"Error calculating accuracy: {e}")
        return {
            "duration_accuracy": 0.0,
            "duration_variance": 0.0,
            "cost_accuracy": 0.0,
            "cost_variance": 0.0,
            "cost_data_points": 0
        }


def _parse_duration_to_months(duration_str: str) -> float:
    """
    Parse duration string to months.
    Handles formats like: "6 months", "6 months, 15 days", "45 days"
    """
    if not duration_str:
        return 0.0
    
    duration_str = duration_str.lower().strip()
    months = 0.0
    days = 0.0
    
    # Extract months
    if "month" in duration_str:
        parts = duration_str.split("month")[0].strip().split()
        if parts:
            try:
                months = float(parts[-1])
            except ValueError:
                pass
    
    # Extract days
    if "day" in duration_str:
        parts = duration_str.split("day")[0].strip().split()
        if parts:
            try:
                days = float(parts[-1])
            except ValueError:
                pass
    
    # Convert to total months
    total_months = months + (days / 30.0)
    return total_months


@router.get("/metrics")
async def get_accuracy_metrics(
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(current_active_user)
):
    """
    Get overall accuracy metrics for the application.
    
    Returns:
        - overall_accuracy: Average accuracy percentage
        - total_projects_analyzed: Number of projects with closeout data
        - duration_accuracy: Average duration estimation accuracy
        - cost_accuracy: Average cost estimation accuracy
        - completion_rate: Average activity completion rate
    """
    try:
        # Build base query for user's projects
        query = select(models.Project).where(
            models.Project.owner_id == current_user.id
        )
        
        # Apply filters
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.where(models.Project.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.where(models.Project.created_at <= end_dt)
        
        if complexity:
            query = query.where(models.Project.complexity == complexity)
        
        if domain:
            query = query.where(models.Project.domain == domain)
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        # Get closeout data from Qdrant
        project_ids = [str(p.id) for p in projects]
        closeout_data = _get_closeout_data_from_qdrant(project_ids)
        
        # Calculate real metrics from closeout data
        if closeout_data:
            all_duration_accuracies = []
            all_duration_variances = []
            all_cost_accuracies = []
            all_cost_variances = []
            
            for project_id, data in closeout_data.items():
                accuracy_info = _calculate_accuracy_from_closeout(data["content"])
                if accuracy_info["duration_accuracy"] > 0:
                    all_duration_accuracies.append(accuracy_info["duration_accuracy"])
                    all_duration_variances.append(accuracy_info["duration_variance"])
                
                # Check based on data existence, not just accuracy > 0
                if accuracy_info.get("cost_data_points", 0) > 0:
                    all_cost_accuracies.append(accuracy_info["cost_accuracy"])
                    all_cost_variances.append(accuracy_info["cost_variance"])
            
            if all_duration_accuracies:
                avg_duration_accuracy = sum(all_duration_accuracies) / len(all_duration_accuracies)
                avg_duration_variance = sum(all_duration_variances) / len(all_duration_variances)
                avg_cost_accuracy = sum(all_cost_accuracies) / len(all_cost_accuracies) if all_cost_accuracies else 0
                avg_cost_variance = sum(all_cost_variances) / len(all_cost_variances) if all_cost_variances else 0
                
                # Calculate overall accuracy as average of duration and cost (if cost data exists)
                if all_cost_accuracies:
                    overall_accuracy = (avg_duration_accuracy + avg_cost_accuracy) / 2
                else:
                    overall_accuracy = avg_duration_accuracy
                
                metrics = {
                    "overall_accuracy": round(overall_accuracy, 1),
                    "total_projects_analyzed": len(closeout_data),
                    "duration_accuracy": round(avg_duration_accuracy, 1),
                    "cost_accuracy": round(avg_cost_accuracy, 1),
                    "completion_rate": 100.0,  # Assume 100% if closeout exists
                    "average_duration_variance": round(avg_duration_variance, 1),
                    "average_cost_variance": round(avg_cost_variance, 1),
                }
            else:
                # No valid closeout data found
                metrics = {
                    "overall_accuracy": 0.0,
                    "total_projects_analyzed": 0,
                    "duration_accuracy": 0.0,
                    "cost_accuracy": 0.0,
                    "completion_rate": 0.0,
                    "average_duration_variance": 0.0,
                    "average_cost_variance": 0.0,
                }
        else:
            # No closeout data found - return zeros
            metrics = {
                "overall_accuracy": 0.0,
                "total_projects_analyzed": 0,
                "duration_accuracy": 0.0,
                "cost_accuracy": 0.0,
                "completion_rate": 0.0,
                "average_duration_variance": 0.0,
                "average_cost_variance": 0.0,
            }
        
        return {
            "status": "success",
            "metrics": metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate metrics: {str(e)}")


@router.get("/projects")
async def get_project_accuracy_breakdown(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(current_active_user)
):
    """
    Get per-project accuracy breakdown.
    
    Returns list of projects with their individual accuracy metrics.
    """
    try:
        # Query user's projects with filters
        query = (
            select(models.Project)
            .where(
                models.Project.owner_id == current_user.id
            )
        )
        
        # Apply filters
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.where(models.Project.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.where(models.Project.created_at <= end_dt)
        
        if complexity:
            query = query.where(models.Project.complexity == complexity)
        
        if domain:
            query = query.where(models.Project.domain == domain)
        
        query = query.order_by(models.Project.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        project_data = []
        
        # Get closeout data for all projects
        project_ids = [str(p.id) for p in projects]
        closeout_data = _get_closeout_data_from_qdrant(project_ids)
        
        for project in projects:
            project_id_str = str(project.id)
            
            # Try to get estimated cost from finalized_scope.json
            estimated_cost_from_scope = 0
            try:
                # Query for finalized_scope.json file
                scope_file_query = select(models.ProjectFile).where(
                    models.ProjectFile.project_id == project.id,
                    models.ProjectFile.file_name == "finalized_scope.json"
                )
                scope_file_result = await db.execute(scope_file_query)
                scope_file = scope_file_result.scalar_one_or_none()
                
                if scope_file:
                    # Download and parse the scope JSON
                    from app.utils.azure_blob import azure_blob
                    import json
                    
                    scope_bytes = await azure_blob.download_bytes(scope_file.file_path)
                    scope_data = json.loads(scope_bytes.decode('utf-8'))
                    
                    # Calculate total cost from resourcing_plan
                    resourcing_plan = scope_data.get('resourcing_plan', [])
                    for resource in resourcing_plan:
                        rate = resource.get('Rate', 0)
                        months = resource.get('Effort Months', 0)
                        estimated_cost_from_scope += rate * months
            except Exception as e:
                # If scope fetch fails, just continue with 0
                pass
            
            # Check if this project has closeout data
            if project_id_str in closeout_data:
                # Parse closeout data to get actual values
                closeout_content = closeout_data[project_id_str]["content"]
                accuracy_info = _calculate_accuracy_from_closeout(closeout_content)
                
                # Extract actual duration from closeout text
                # Try to get calendar duration from project-level dates first
                start_date_pattern = r"ACTUAL START DATE:\s*(\d{4}-\d{2}-\d{2})"
                end_date_pattern = r"ACTUAL END DATE:\s*(\d{4}-\d{2}-\d{2})"
                
                start_match = re.search(start_date_pattern, closeout_content, re.IGNORECASE)
                end_match = re.search(end_date_pattern, closeout_content, re.IGNORECASE)
                
                calendar_duration = None
                if start_match and end_match:
                    try:
                        from datetime import datetime
                        start_date = datetime.strptime(start_match.group(1), "%Y-%m-%d")
                        end_date = datetime.strptime(end_match.group(1), "%Y-%m-%d")
                        days_diff = (end_date - start_date).days
                        calendar_duration = round(days_diff / 30.0, 1)  # Convert to months
                    except Exception as e:
                        logger.warning(f"Failed to parse project dates: {e}")
                
                # Calculate total effort (sum of activity durations)
                act_pattern = r"ACTUAL DURATION:\s*([\d.]+)\s*months?"
                act_matches = re.findall(act_pattern, closeout_content, re.IGNORECASE)
                
                total_effort = 0
                if act_matches:
                    total_effort = sum(float(duration) for duration in act_matches)
                
                # Use calendar duration if available, otherwise fall back to total effort
                if calendar_duration is not None:
                    actual_duration = f"{calendar_duration} months"
                elif total_effort > 0:
                    actual_duration = f"{total_effort} months"
                else:
                    actual_duration = "N/A"
                
                # Extract cost values from closeout (these override scope estimates)
                estimated_cost = accuracy_info.get("total_estimated_cost", 0)
                actual_cost = accuracy_info.get("total_actual_cost", 0)
                
                # If closeout has no estimated cost but scope does, use scope estimate
                if estimated_cost == 0 and estimated_cost_from_scope > 0:
                    estimated_cost = estimated_cost_from_scope
                
                project_data.append({
                    "id": project_id_str,
                    "name": project.name,
                    "domain": project.domain,
                    "complexity": project.complexity,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "estimated_duration": project.duration,
                    "actual_duration": actual_duration,  # Calendar duration from dates
                    "total_effort": f"{total_effort} months" if total_effort > 0 else "N/A",  # Sum of activities
                    "duration_accuracy": accuracy_info["duration_accuracy"],
                    "estimated_cost": f"${estimated_cost:,.2f}" if estimated_cost > 0 else "N/A",
                    "actual_cost": f"${actual_cost:,.2f}" if actual_cost > 0 else "N/A",
                    "cost_accuracy": accuracy_info["cost_accuracy"],
                    "activities_completed": accuracy_info.get("activities_count", "N/A"),
                    "completion_rate": 100.0 if accuracy_info["duration_accuracy"] > 0 else 0.0
                })
            else:
                # No closeout data - show scope-based estimates
                project_data.append({
                    "id": project_id_str,
                    "name": project.name,
                    "domain": project.domain,
                    "complexity": project.complexity,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "estimated_duration": project.duration,
                    "actual_duration": "N/A",
                    "total_effort": "N/A",
                    "duration_accuracy": 0.0,
                    "estimated_cost": f"${estimated_cost_from_scope:,.2f}" if estimated_cost_from_scope > 0 else "N/A",
                    "actual_cost": "N/A",
                    "cost_accuracy": 0.0,
                    "activities_completed": "N/A",
                    "completion_rate": 0.0
                })
        
        return {
            "status": "success",
            "count": len(project_data),
            "projects": project_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project breakdown: {str(e)}")


@router.get("/trends")
async def get_accuracy_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(current_active_user)
):
    """
    Get historical accuracy trends over time.
    
    Returns monthly accuracy data for charting.
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # Query projects in date range
        query = select(models.Project).where(
            models.Project.owner_id == current_user.id,
            models.Project.created_at >= start_date
        )
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        # Get closeout data for all projects
        project_ids = [str(p.id) for p in projects]
        closeout_data = _get_closeout_data_from_qdrant(project_ids)
        
        # Group projects by month and calculate real accuracy
        monthly_data = {}
        
        for project in projects:
            project_id_str = str(project.id)
            
            # Get month key from project creation date
            if project.created_at:
                month_key = project.created_at.strftime("%Y-%m")
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        "duration_accuracies": [],
                        "cost_accuracies": [],
                        "projects_count": 0
                    }
                
                # If project has closeout data, calculate accuracy
                if project_id_str in closeout_data:
                    closeout_content = closeout_data[project_id_str]["content"]
                    accuracy_info = _calculate_accuracy_from_closeout(closeout_content)
                    
                    if accuracy_info["duration_accuracy"] > 0:
                        monthly_data[month_key]["duration_accuracies"].append(accuracy_info["duration_accuracy"])
                    
                    if accuracy_info.get("cost_data_points", 0) > 0:
                        monthly_data[month_key]["cost_accuracies"].append(accuracy_info["cost_accuracy"])
                    
                    monthly_data[month_key]["projects_count"] += 1
        
        # Build trends array for all requested months
        trends = []
        for i in range(months):
            month_date = end_date - timedelta(days=(months - i - 1) * 30)
            month_key = month_date.strftime("%Y-%m")
            
            if month_key in monthly_data and monthly_data[month_key]["projects_count"] > 0:
                data = monthly_data[month_key]
                
                # Calculate averages
                duration_acc = sum(data["duration_accuracies"]) / len(data["duration_accuracies"]) if data["duration_accuracies"] else 0
                cost_acc = sum(data["cost_accuracies"]) / len(data["cost_accuracies"]) if data["cost_accuracies"] else 0
                
                # Overall is average of duration and cost (if cost exists)
                if cost_acc > 0:
                    overall_acc = (duration_acc + cost_acc) / 2
                else:
                    overall_acc = duration_acc
                
                trends.append({
                    "month": month_key,
                    "overall_accuracy": round(overall_acc, 1),
                    "duration_accuracy": round(duration_acc, 1),
                    "cost_accuracy": round(cost_acc, 1),
                    "projects_count": data["projects_count"]
                })
            else:
                # No data for this month - show 0
                trends.append({
                    "month": month_key,
                    "overall_accuracy": 0,
                    "duration_accuracy": 0,
                    "cost_accuracy": 0,
                    "projects_count": 0
                })
        
        return {
            "status": "success",
            "trends": trends
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate trends: {str(e)}")
