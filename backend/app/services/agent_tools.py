"""
Agent Tools for Project Scoping

These tools give the agent capabilities to:
- Search knowledge bases
- Find case studies
- Get accurate rate cards
- Calculate costs

Each tool is a function that the agent can call autonomously.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import tool

from app.utils.ai_clients import embed_text_azure, get_qdrant_client
from app.config.config import QDRANT_COLLECTION, CASE_STUDY_COLLECTION
from app.models import RateCard

logger = logging.getLogger(__name__)


@tool
def search_knowledge_base(query: str, limit: int = 5) -> str:
    """
    Search the knowledge base for relevant information.
    
    Use this when you need:
    - Best practices
    - Technical guidelines
    - Implementation patterns
    - Architecture recommendations
    
    Args:
        query: Search query (e.g., "CRM authentication best practices")
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        String containing relevant knowledge base content
    """
    try:
        logger.info(f"🔍 Agent searching KB: {query}")
        
        qdrant = get_qdrant_client()
        
        # Generate embedding for query
        query_vector = embed_text_azure([query])[0]
        
        # Search Qdrant
        results = qdrant.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=limit
        )
        
        if not results:
            return "No relevant information found in knowledge base."
        
        # Extract and format content
        chunks = []
        for i, result in enumerate(results, 1):
            content = result.payload.get('content', '')
            file_name = result.payload.get('file_name', 'Unknown')
            score = result.score
            
            chunks.append(f"""
**Result {i}** (Relevance: {score:.2f})
Source: {file_name}

{content}
""".strip())
        
        formatted_result = "\n\n---\n\n".join(chunks)
        logger.info(f"✅ Found {len(results)} KB results")
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ KB search failed: {e}")
        return f"Error searching knowledge base: {str(e)}"


@tool
def find_case_studies(domain: str, tech_stack: str = "", limit: int = 3) -> str:
    """
    Find similar past projects and case studies.
    
    Use this to:
    - Learn from similar projects
    - Get realistic timelines
    - Understand team compositions
    - See what worked/didn't work
    
    Args:
        domain: Project domain (e.g., "CRM", "E-commerce", "Analytics")
        tech_stack: Optional tech stack (e.g., "Python React PostgreSQL")
        limit: Maximum number of case studies to return (default: 3)
    
    Returns:
        String containing case study information
    """
    try:
        logger.info(f"🔍 Agent searching case studies: {domain} {tech_stack}")
        
        qdrant = get_qdrant_client()
        
        # Build search query
        query = f"{domain} {tech_stack}".strip()
        query_vector = embed_text_azure([query])[0]
        
        # Search case study collection
        results = qdrant.search(
            collection_name=CASE_STUDY_COLLECTION,
            query_vector=query_vector,
            limit=limit
        )
        
        if not results:
            return f"No case studies found for domain: {domain}"
        
        # Format case studies
        case_studies = []
        for i, result in enumerate(results, 1):
            payload = result.payload
            
            # Try to get structured metadata
            client_name = payload.get('client_name', 'Unknown Client')
            overview = payload.get('overview', '')
            solution = payload.get('solution', '')
            impact = payload.get('impact', '')
            content = payload.get('content', '')
            
            case_study_text = f"""
**Case Study {i}: {client_name}** (Relevance: {result.score:.2f})

Overview: {overview or content[:200]}

Solution: {solution}

Impact/Results: {impact}
""".strip()
            
            case_studies.append(case_study_text)
        
        formatted_result = "\n\n---\n\n".join(case_studies)
        logger.info(f"✅ Found {len(results)} case studies")
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ Case study search failed: {e}")
        return f"Error searching case studies: {str(e)}"


# Note: This tool needs database session, so we'll create a wrapper
async def get_rate_cards_async(company_id: str, db_session: AsyncSession) -> Dict[str, float]:
    """
    Get accurate rate cards from the database.
    
    **CRITICAL**: ALWAYS use this for cost calculations - NEVER guess rates!
    
    Args:
        company_id: Company/client ID
        db_session: Database session
    
    Returns:
        Dictionary of {role: rate_per_month}
    """
    try:
        logger.info(f"💰 Agent fetching rate cards for company: {company_id}")
        
        # Query database for rate cards
        result = await db_session.execute(
            select(RateCard).where(RateCard.company_id == company_id)
        )
        rate_cards = result.scalars().all()
        
        if not rate_cards:
            logger.warning(f"⚠️  No custom rates found, using default Sigmoid rates")
            # Return default Sigmoid rates
            default_rates = {
                "Backend Developer": 3000.0,
                "Frontend Developer": 2800.0,
                "Full Stack Developer": 3200.0,
                "QA Engineer": 2000.0,
                "QA Analyst": 1800.0,
                "Data Engineer": 2800.0,
                "DevOps Engineer": 3200.0,
                "Project Manager": 3500.0,
                "Business Analyst": 2500.0,
                "UI/UX Designer": 2600.0,
                "Solution Architect": 4000.0,
                "Cloud Engineer": 3000.0,
                "Security Engineer": 3200.0,
            }
            return default_rates
        
        # Convert to dictionary
        rates = {rc.role: float(rc.rate) for rc in rate_cards}
        logger.info(f"✅ Retrieved {len(rates)} rate cards")
        
        return rates
        
    except Exception as e:
        logger.error(f"❌ Rate card fetch failed: {e}")
        raise


@tool
def calculate_project_cost(team_composition: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate total project cost from team composition.
    
    Use this after you've:
    1. Determined team composition (roles and counts)
    2. Retrieved accurate rates using get_rate_cards
    3. Estimated the timeline
    
    Args:
        team_composition: List of team members with structure:
            [
                {
                    "role": "Backend Developer",
                    "count": 2,
                    "rate_per_month": 3000,
                    "total_months": 6
                },
                ...
            ]
    
    Returns:
        Dictionary with total cost and breakdown
    """
    try:
        logger.info(f"💵 Agent calculating project cost for {len(team_composition)} roles")
        
        total_cost = 0
        breakdown = []
        
        for item in team_composition:
            role = item.get('role', 'Unknown')
            count = item.get('count', 1)
            rate = item.get('rate_per_month', 0)
            months = item.get('total_months', 0)
            
            subtotal = count * rate * months
            total_cost += subtotal
            
            breakdown.append({
                "role": role,
                "count": count,
                "rate_per_month": rate,
                "total_months": months,
                "subtotal": subtotal
            })
        
        result = {
            "total_cost": total_cost,
            "breakdown_by_role": breakdown,
            "currency": "USD"
        }
        
        logger.info(f"✅ Total cost calculated: ${total_cost:,.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Cost calculation failed: {e}")
        return {
            "error": str(e),
            "total_cost": 0,
            "breakdown_by_role": []
        }


# Export tools for agent
def get_agent_tools():
    """
    Get list of tools for the agent.
    
    Note: get_rate_cards is handled separately since it needs DB session.
    """
    return [
        search_knowledge_base,
        find_case_studies,
        calculate_project_cost
    ]
