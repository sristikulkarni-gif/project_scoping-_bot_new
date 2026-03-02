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

        # Build generation prompt - DO NOT use actual project/client names
        prompt = f"""You are an expert case study writer. Generate a professional case study for a RELATED project that is SIMILAR to (but NOT the same as) the project described below.

**IMPORTANT INSTRUCTIONS:**
- DO NOT use the project name "{project_name}" as the client name
- DO NOT create a case study about this exact project
- INSTEAD: Create a case study about a DIFFERENT, SIMILAR client in the same industry/domain
- The case study should be RELATED and demonstrate similar challenges/solutions
- Use a DIFFERENT client name (but same industry if possible)

**PROJECT CONTEXT (for reference only - DO NOT copy exactly):**
- Project Domain: {domain}
- Use Cases: {use_cases or "Not specified"}
- Complexity: {complexity or "Medium"}
- Tech Stack: {tech_stack or "Modern technology stack"}
- Compliance: {compliance or "Standard compliance"}

**EXECUTIVE SUMMARY:**
{executive_summary}
{rfp_section}
**TASK:**
Generate a RELATED case study from a DIFFERENT client with SIMILAR challenges.

**EXAMPLES OF GOOD CLIENT NAMES (based on domain):**
- Data Analytics/AI: "TechCorp Global", "DataDrive Solutions", "Analytics Innovators Inc"
- Finance/Banking: "FinServe International", "Capital Solutions Group"
- Healthcare: "MedTech Systems", "HealthCare Innovations"
- Retail/E-commerce: "RetailPro Enterprises", "E-Commerce Solutions Ltd"
- Manufacturing: "Industrial Automation Corp", "Manufacturing Systems Inc"

**OUTPUT FORMAT** (JSON only):
{{
  "client_name": "A DIFFERENT client name (NOT '{project_name}' or parts of it)",
  "overview": "2-3 sentences describing this DIFFERENT client's similar business challenge. Make it related but NOT identical to the project context above.",
  "solution": "3-4 sentences describing how Sigmoid delivered a similar solution for this client. Use similar technologies and approaches but make it a completed past project.",
  "impact": "2-3 sentences with measurable outcomes (10-50% improvements). Example: '35% faster data processing', 'Reduced costs by 20%', 'Improved accuracy to 95%'."
}}

**CRITICAL RULES:**
1. Client name MUST be different from "{project_name}"
2. Client name should NOT contain words from the project title
3. Make it a SIMILAR but SEPARATE case study
4. Use realistic metrics and business language
5. Output ONLY valid JSON

Generate the RELATED case study now:"""

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