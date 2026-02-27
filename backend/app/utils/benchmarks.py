import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

BENCHMARKS_FILE = Path(__file__).parent.parent / "data" / "benchmarks.json"

def load_benchmarks() -> Dict[str, Any]:
    try:
        if BENCHMARKS_FILE.exists():
            with open(BENCHMARKS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load benchmarks file: {e}")
    return {}

def validate_against_benchmark(scope: Dict[str, Any], domain: str, complexity: str) -> List[str]:
    """
    Validates a generated scope against industry benchmarks based on domain and complexity.
    Returns a list of warning strings if the estimate is out of benchmark range.
    """
    warnings = []
    
    # 1. Load benchmarks
    benchmarks = load_benchmarks()
    if not benchmarks:
        return warnings

    # Normalize inputs
    domain_key = _normalize_domain(domain)
    complexity_key = _normalize_complexity(complexity)

    # 2. Find matching benchmark category
    # Fallback to general if specific domain isn't found
    category = benchmarks.get(domain_key, benchmarks.get("general", {}))
    
    # Get specific complexity threshold
    thresholds = category.get(complexity_key)
    
    if not thresholds:
        logger.info(f"No benchmark thresholds found for domain '{domain_key}' and complexity '{complexity_key}'")
        return warnings

    # 3. Extract metrics from scope
    try:
        # Extract total duration in months
        duration_str = scope.get("overview", {}).get("Duration", "0 months")
        import re
        match = re.search(r"(\d+(\.\d+)?)", str(duration_str))
        actual_months = float(match.group(1)) if match else 0.0

        # Extract total cost
        # The cost is usually summing up resourcing_plan
        resourcing_plan = scope.get("resourcing_plan", [])
        actual_cost = sum(entry.get("Cost", 0) for entry in resourcing_plan)
        
        # 4. Compare vs Thresholds
        min_months = thresholds.get("min_months", 0)
        max_months = thresholds.get("max_months", 999)
        min_cost = thresholds.get("min_cost_usd", 0)

        logger.info(f"📊 Benchmark Check -> Actual Months: {actual_months} (Range: {min_months}-{max_months}), Actual Cost: {actual_cost} (Min: {min_cost})")

        if actual_months > 0:
            if actual_months < min_months * 0.75: # 25% tolerance below
                warnings.append(f"⚠️ Timeline is unusually fast ({actual_months} months). Industry average for {complexity_key} {domain} is {min_months}-{max_months} months.")
            elif actual_months > max_months * 1.5: # 50% tolerance above
                warnings.append(f"⚠️ Timeline is significantly longer ({actual_months} months) than the industry benchmark ({min_months}-{max_months} months).")
        
        if actual_cost > 0 and actual_cost < min_cost * 0.5: # If half of the minimum cost
            warnings.append(f"⚠️ Estimated cost (${actual_cost:,.0f}) is remarkably low. Benchmarks suggest at least ${min_cost:,.0f} for {complexity_key} complexity projects in this domain.")

    except Exception as e:
        logger.error(f"Error during benchmark validation: {e}")

    return warnings

def _normalize_domain(domain: str) -> str:
    """Normalize user domain strings to match benchmark json keys"""
    if not domain:
        return "general"
    
    d = str(domain).lower().strip()
    if "data" in d:
        return "data_platform"
    if "crm" in d or "salesforce" in d or "hubspot" in d:
        return "crm"
    if "mobile" in d or "ios" in d or "android" in d:
        return "mobile_app"
    if "web" in d or "portal" in d or "e-commerce" in d:
        return "web_application"
    
    return "general"

def _normalize_complexity(complexity: str) -> str:
    """Normalize complexity strings to low/medium/high"""
    if not complexity:
        return "medium"
    
    c = str(complexity).lower().strip()
    if "low" in c or "simple" in c or "easy" in c:
        return "low"
    if "high" in c or "complex" in c or "hard" in c:
        return "high"
        
    return "medium"
