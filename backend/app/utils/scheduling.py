import logging
import math
from datetime import datetime, timedelta
import networkx as nx
from typing import List, Dict, Any

from app.schemas import ActivityItem

logger = logging.getLogger(__name__)

def round_to_half(value: float) -> float:
    if value == 0:
        return 0.0
    return round(value * 2) / 2

def calculate_project_schedule(activities: List[ActivityItem], start_date_str: str) -> Dict[str, Any]:
    """
    Takes a list of Phase 2 ActivityItems (which have effort_months and dependencies, but no dates)
    and uses a Critical Path Method (CPM) algorithm via NetworkX to calculate exact dates.
    
    Returns:
    - enriched_activities: The same activities but with `start_date` and `end_date` mapped.
    - total_duration_months: The mathematically accurate total duration.
    """
    logger.info(f"📅 Calculating schedule deterministically for {len(activities)} activities")

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Invalid start date: {start_date_str}. Defaulting to today.")
        start_date = datetime.now()

    # Build the directed graph
    G = nx.DiGraph()

    # Create a mapping for name -> ActivityItem for easy lookup
    # Normalize names to lowercase for robust dependency matching
    activity_map = {}
    for act in activities:
        node_id = act.name.strip().lower()
        activity_map[node_id] = act
        # effort_days approx (1 month = 30 days)
        effort_days = int(math.ceil(act.effort_months * 30))
        # Ensure minimum 1 day
        effort_days = max(1, effort_days)
        G.add_node(node_id, effort_days=effort_days, original_name=act.name)

    # Add edges based on dependencies
    for act in activities:
        node_id = act.name.strip().lower()
        for dep in act.dependencies:
            dep_id = dep.strip().lower()
            # If the dependent task exists in our list, add an edge: dep -> node
            if dep_id in activity_map:
                G.add_edge(dep_id, node_id)
            else:
                logger.warning(f"⚠️ Activity '{act.name}' depends on '{dep}', but '{dep}' does not exist in the activity list.")

    # Check for cycles (impossible schedules like A -> B -> A)
    try:
        cycles = list(nx.simple_cycles(G))
        if cycles:
            logger.error(f"❌ Dependency cycle(s) detected: {cycles}. breaking cycles.")
            for cycle in cycles:
                # Break the cycle by removing the last edge
                G.remove_edge(cycle[-1], cycle[0])
    except Exception as e:
        logger.warning(f"Cycle detection failed: {e}")

    # Calculate earliest start times (CPM Forward Pass)
    # distance[node] will be tracking the latest end_date (in days from project start) of all its predecessors
    earliest_start_days = {node: 0 for node in G.nodes()}

    # Topological sort ensures we process nodes only after their predecessors are processed
    for node in nx.topological_sort(G):
        # The node ends at its start day + its own duration
        node_end_day = earliest_start_days[node] + G.nodes[node]['effort_days']
        
        # Propagate this end_day to all successors: 
        # a successor cannot start until ALL its predecessors finish, so it takes the MAX end_day.
        for successor in G.successors(node):
            earliest_start_days[successor] = max(
                earliest_start_days[successor], 
                node_end_day
            )

    # Reconstruct the final list with dates
    enriched_activities = []
    max_end_date = start_date

    # To maintain the original order, iterate through the input list
    current_id = 1
    for act in activities:
        node_id = act.name.strip().lower()
        
        start_offset_days = earliest_start_days.get(node_id, 0)
        duration_days = G.nodes[node_id].get('effort_days', 1)
        
        act_start_date = start_date + timedelta(days=start_offset_days)
        # End date is start date + duration (minus 1 to not overcount)
        act_end_date = act_start_date + timedelta(days=duration_days - 1)
        
        if act_end_date > max_end_date:
            max_end_date = act_end_date

        # Format into the legacy output dictionary format expected by the frontend
        enriched_activities.append({
            "ID": current_id,
            "Activities": act.name,
            "Phase": act.phase,
            "Owner": act.owner,
            "Resources": ", ".join(act.dependencies) if act.dependencies else "None",  # legacy field
            "Start Date": act_start_date.strftime("%Y-%m-%d"),
            "End Date": act_end_date.strftime("%Y-%m-%d"),
            "Effort Months": act.effort_months
        })
        current_id += 1

    # Calculate exact total months
    total_days = (max_end_date - start_date).days + 1
    total_duration_months = round_to_half(total_days / 30.0)
    
    logger.info(f"✅ Scheduling complete. Total duration: {total_duration_months} months.")

    return {
        "activities": enriched_activities,
        "total_duration_months": total_duration_months,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": max_end_date.strftime("%Y-%m-%d")
    }
