"""
AI-based case study generation for projects without matching case studies.
"""
import logging
import json
import re
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def generate_synthetic_case_study(
    db: AsyncSession,
    project,
    executive_summary: str,
    rfp_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a synthetic case study using LLM when no matching case study is found.

    Args:
        db: Database session
        project: Project model instance
        executive_summary: Executive summary from project scope
        rfp_text: Optional RFP document text

    Returns:
        Dictionary with case study fields: client_name, overview, solution, impact
    """
    from app.utils.scope_engine import ollama_chat
    from app.config.config import OLLAMA_MODEL

    try:
        # Build context from project data
        project_name = getattr(project, "name", "Unnamed Project")
        domain = getattr(project, "domain", "Technology")
        use_cases = getattr(project, "use_cases", "")
        complexity = getattr(project, "complexity", "")
        tech_stack = getattr(project, "tech_stack", "")
        compliance = getattr(project, "compliance", "")

        # Get company information if available
        client_name = "Sample Client"
        try:
            if getattr(project, "company", None):
                client_name = getattr(project.company, "name", "Sample Client")
        except:
            pass

        # Build RFP section if available
        rfp_section = ""
        if rfp_text and len(rfp_text) > 100:
            rfp_section = f"\n**RFP DOCUMENT EXCERPT:**\n{rfp_text[:2000]}\n"

        # Build generation prompt
        prompt = f"""You are an expert case study writer. Generate a professional case study based on the following project information.

**PROJECT INFORMATION:**
- Client Name: {client_name}
- Project Title: {project_name}
- Domain: {domain}
- Use Cases: {use_cases or "Not specified"}
- Complexity: {complexity or "Medium"}
- Tech Stack: {tech_stack or "Modern technology stack"}
- Compliance Requirements: {compliance or "Standard compliance"}

**EXECUTIVE SUMMARY:**
{executive_summary}
{rfp_section}
**TASK:**
Generate a professional case study with the following sections. Make it realistic, specific, and impactful.

**OUTPUT FORMAT** (JSON only, no explanations):
{{
  "client_name": "{client_name}",
  "overview": "2-3 sentence overview describing the client's business challenge and objectives. Focus on the problem they needed to solve and why.",
  "solution": "3-4 sentences describing the solution approach, key technologies used, and implementation strategy. Be specific about methodologies and technical decisions.",
  "impact": "2-3 sentences describing measurable business outcomes, improvements, or benefits achieved. Include specific metrics or percentages if possible (e.g., '30% reduction in processing time')."
}}

**GUIDELINES:**
1. Keep it professional and realistic
2. Use third-person perspective
3. Make metrics believable (10-50% improvements are realistic)
4. Focus on business value, not just technical details
5. Ensure overview flows into solution, and solution flows into impact
6. Output ONLY valid JSON, nothing else

Generate the case study now:"""

        # Call LLM
        logger.info(f"🤖 Generating synthetic case study for project {project.id}")
        response = ollama_chat(prompt, model=OLLAMA_MODEL, temperature=0.7, format_json=True)

        # Parse response
        case_study_data = _extract_case_study_from_response(response, client_name)

        logger.info(f"✅ Generated synthetic case study: {case_study_data['client_name']}")
        return case_study_data

    except Exception as e:
        logger.error(f"Failed to generate synthetic case study: {e}")
        # Return fallback case study
        return _get_fallback_case_study(client_name, project_name, domain)


def _extract_case_study_from_response(response: str, default_client_name: str) -> Dict[str, Any]:
    """
    Extract and validate case study data from LLM response.
    """
    try:
        # Try to parse as JSON
        if isinstance(response, str):
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                response = json_match.group()

            parsed = json.loads(response)
        else:
            parsed = response

        # Validate required fields
        required_fields = ["client_name", "overview", "solution", "impact"]
        for field in required_fields:
            if field not in parsed or not parsed[field]:
                raise ValueError(f"Missing required field: {field}")

        # Ensure reasonable lengths
        if len(parsed["overview"]) < 50:
            raise ValueError("Overview too short")
        if len(parsed["solution"]) < 100:
            raise ValueError("Solution too short")
        if len(parsed["impact"]) < 50:
            raise ValueError("Impact too short")

        return {
            "client_name": parsed["client_name"],
            "overview": parsed["overview"].strip(),
            "solution": parsed["solution"].strip(),
            "impact": parsed["impact"].strip()
        }

    except Exception as e:
        logger.warning(f"Failed to parse LLM response: {e}")
        raise


def _get_fallback_case_study(client_name: str, project_name: str, domain: str) -> Dict[str, Any]:
    """
    Generate a basic fallback case study if LLM generation fails.
    """
    return {
        "client_name": client_name,
        "overview": f"{client_name} required a comprehensive {domain} solution to modernize their infrastructure and improve operational efficiency. The project aimed to address scalability challenges and streamline business processes.",
        "solution": f"Our team designed and implemented a {domain}-focused solution leveraging modern technologies and best practices. The implementation included system architecture design, development of core features, integration with existing systems, and comprehensive testing to ensure reliability and performance.",
        "impact": f"The solution delivered significant improvements in operational efficiency and user experience. {client_name} achieved better system performance, reduced operational costs by approximately 25%, and improved their ability to scale operations to meet growing business demands.",
    }