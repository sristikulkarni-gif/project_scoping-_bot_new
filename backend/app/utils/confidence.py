import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def calculate_confidence(
    past_proposals_found: int,
    benchmark_warnings: List[str],
    is_closed_override: bool = False
) -> Dict[str, Any]:
    """
    Calculates a confidence score (0-100) and returns reasons for the score.
    
    Signals:
    - Base score: 50
    - Past proposals found: +15 each (max +45)
    - Benchmark warnings: -15 each
    - Explicit closeout override (user provided actuals): Automatically 100
    
    Returns:
        {
            "score": 100,
            "reasons": ["High confidence: Actuals directly applied from closed project."]
        }
    """
    if is_closed_override:
        return {
            "score": 100,
            "reasons": ["High confidence: Scope effort metrics were overridden using exact actuals from a previously closed project."]
        }
    
    reasons = []
    score = 50
    
    if past_proposals_found > 0:
        bonus = min(past_proposals_found * 15, 45)
        score += bonus
        reasons.append(f"Found {past_proposals_found} similar past proposals for calibration (+{bonus} pts).")
    else:
        reasons.append("No similar past proposals found for calibration. Relying entirely on LLM baseline.")
        
    if benchmark_warnings:
        penalty = len(benchmark_warnings) * 15
        score -= penalty
        reasons.append(f"Generated scope deviates from industry benchmarks in {len(benchmark_warnings)} areas (-{penalty} pts).")
        
    score = max(0, min(100, score))
    
    if score >= 75:
        reasons.append("Overall: High Confidence.")
    elif score >= 40:
        reasons.append("Overall: Moderate Confidence. PM Review Recommended.")
    else:
        reasons.append("Overall: Low Confidence. Senior Review Required.")
        
    return {
        "score": score,
        "reasons": reasons
    }
