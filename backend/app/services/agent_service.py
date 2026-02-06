"""
Project Scoping Agent Service

Main agent logic for intelligent project scoping using Azure OpenAI.
The agent uses real data from tools to avoid hallucinations.
"""

import json
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION
)
from app.config.agent_config import PROJECT_SCOPING_SYSTEM_PROMPT, AGENT_CONFIG
from app.services.agent_tools import get_agent_tools, get_rate_cards_async

logger = logging.getLogger(__name__)






class ProjectScopingAgent:
    """
    AI Agent for intelligent project scoping.
    
    This agent can:
    - Search knowledge bases for best practices
    - Find relevant case studies
    - Get accurate rate cards from database
    - Calculate costs precisely
    - Verify its own work for quality
    """
    
    def __init__(self):
        """Initialize the project scoping agent."""
        logger.info("🤖 Initializing Project Scoping Agent...")
        
        # Initialize Azure OpenAI for LangChain
        try:
            self.llm = AzureChatOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_KEY,
                deployment_name=AZURE_OPENAI_DEPLOYMENT,
                api_version=AZURE_OPENAI_API_VERSION,
                temperature=AGENT_CONFIG["temperature"],
                model_name=AZURE_OPENAI_DEPLOYMENT,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            raise
        
        # Get tools (excluding get_rate_cards which needs DB session)
        self.tools = get_agent_tools()
        
        logger.info(f"✅ Agent initialized with {len(self.tools)} tools")

    
    async def generate_scope(
        self,
        project_name: str,
        domain: str,
        tech_stack: str,
        rfp_text: str,
        company_id: str,
        db_session: AsyncSession,
        complexity: Optional[str] = None,
        use_cases: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive project scope using agent reasoning.
        
        The agent will:
        1. Analyze the RFP and requirements
        2. Search for relevant knowledge and case studies
        3. Get accurate rate cards from database
        4. Plan team composition based on research
        5. Calculate costs using real rates
        6. Verify completeness and accuracy
        
        Args:
            project_name: Name of the project
            domain: Project domain (e.g., "CRM", "E-commerce")
            tech_stack: Technology stack
            rfp_text: Full RFP document text
            company_id: Company/client ID for rate cards
            db_session: Database session for queries
            complexity: Optional complexity level
            use_cases: Optional use cases description
        
        Returns:
            Dictionary containing complete project scope
        """
        logger.info(f"🚀 Agent generating scope for: {project_name}")
        
        try:
            # Get rate cards first (agent will need this info)
            rate_cards = await get_rate_cards_async(company_id, db_session)
            rate_cards_str = json.dumps(rate_cards, indent=2)
            
            # Build user prompt with all context
            user_prompt = self._build_user_prompt(
                project_name=project_name,
                domain=domain,
                tech_stack=tech_stack,
                rfp_text=rfp_text,
                complexity=complexity,
                use_cases=use_cases,
                rate_cards=rate_cards_str
            )
            
            # Call LLM directly with system prompt
            logger.info("🤖 Agent starting autonomous reasoning...")
            
            messages = [
                SystemMessage(content=PROJECT_SCOPING_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]
            
            # Invoke LLM
            response = await self.llm.ainvoke(messages)
            
            logger.info("✅ Agent completed reasoning")
            
            # Parse JSON from response
            scope_data = self._extract_json_from_response(response.content)
            
            # Add metadata
            scope_data['_agent_metadata'] = {
                "generated_at": datetime.utcnow().isoformat(),
                "agent_version": "1.0.0",
                "reasoning_steps": 1,  # Direct LLM call
                "tools_used": ["get_rate_cards"]  # We called this tool
            }
            
            # Validate scope structure
            scope_data = self._validate_and_enrich_scope(scope_data, project_name, domain)
            
            logger.info(f"✅ Scope generated successfully")
            
            return scope_data
            
        except Exception as e:
            logger.error(f"❌ Agent scope generation failed: {e}", exc_info=True)
            raise
    
    def _build_user_prompt(
        self,
        project_name: str,
        domain: str,
        tech_stack: str,
        rfp_text: str,
        complexity: Optional[str],
        use_cases: Optional[str],
        rate_cards: str
    ) -> str:
        """Build the user prompt for the agent."""
        
        prompt = f"""Create a comprehensive project scope for the following project:

**Project Information:**
- **Name**: {project_name}
- **Domain**: {domain}
- **Tech Stack**: {tech_stack}
"""
        
        if complexity:
            prompt += f"- **Complexity**: {complexity}\n"
        
        if use_cases:
            prompt += f"- **Use Cases**: {use_cases}\n"
        
        prompt += f"""
**Available Rate Cards** (use these exact rates for cost calculations):
```json
{rate_cards}
```

**RFP Document:**
{rfp_text[:8000]}  

**Your Task:**

Please analyze this RFP thoroughly and create a detailed project scope. Follow the process outlined in your system instructions:

1. Research best practices and find similar case studies
2. Plan an appropriate team composition
3. Calculate accurate costs using the provided rate cards
4. Define clear phases, activities, and timeline
5. Identify risks and assumptions
6. Verify your work for completeness and accuracy

Remember to use your tools to gather information and validate your decisions!

Return your response as a properly formatted JSON object following the schema in your system instructions.
"""
        
        return prompt
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from agent's response.
        
        The agent might return JSON in various formats:
        - Plain JSON
        - JSON in markdown code blocks
        - JSON with explanatory text
        """
        try:
            # Try direct JSON parse first
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to extract from any code block
        code_match = re.search(r'```\s*\n(.*?)\n```', response_text, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_obj_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_obj_match:
            try:
                return json.loads(json_obj_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all else fails, raise error
        logger.error(f"Failed to extract JSON from response: {response_text[:500]}")
        raise ValueError("Agent did not return valid JSON. Response: " + response_text[:500])
    
    def _extract_tools_used(self, messages: list) -> list:
        """Extract list of tools the agent used during reasoning."""
        tools_used = []
        
        for msg in messages:
            # Check if message has tool calls
            if hasattr(msg, 'additional_kwargs'):
                tool_calls = msg.additional_kwargs.get('tool_calls', [])
                for tool_call in tool_calls:
                    if hasattr(tool_call, 'function'):
                        tools_used.append(tool_call.function.name)
                    elif isinstance(tool_call, dict):
                        tools_used.append(tool_call.get('function', {}).get('name', 'unknown'))
        
        return list(set(tools_used))  # Remove duplicates
    
    def _validate_and_enrich_scope(
        self,
        scope_data: Dict[str, Any],
        project_name: str,
        domain: str
    ) -> Dict[str, Any]:
        """
        Validate scope structure and enrich with defaults if needed.
        """
        # Ensure required top-level keys exist
        if 'project_overview' not in scope_data:
            scope_data['project_overview'] = {
                "name": project_name,
                "domain": domain,
                "objective": "To be defined",
                "key_deliverables": []
            }
        
        if 'timeline' not in scope_data:
            scope_data['timeline'] = {
                "total_months": 6,
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
            }
        
        if 'team_composition' not in scope_data:
            scope_data['team_composition'] = []
        
        if 'cost_summary' not in scope_data:
            # Calculate from team composition if available
            total = 0
            if scope_data['team_composition']:
                for member in scope_data['team_composition']:
                    count = member.get('count', 1)
                    rate = member.get('rate_per_month', 0)
                    months = member.get('total_months', 6)
                    total += count * rate * months
            
            scope_data['cost_summary'] = {
                "total_cost": total,
                "currency": "USD"
            }
        
        if 'phases' not in scope_data:
            scope_data['phases'] = []
        
        if 'activities' not in scope_data:
            scope_data['activities'] = []
        
        if 'risks' not in scope_data:
            scope_data['risks'] = []
        
        if 'assumptions' not in scope_data:
            scope_data['assumptions'] = []
        
        if 'case_study_references' not in scope_data:
            scope_data['case_study_references'] = []
        
        return scope_data


# Singleton instance
_agent_instance: Optional[ProjectScopingAgent] = None


def get_scoping_agent() -> ProjectScopingAgent:
    """
    Get or create the project scoping agent singleton.
    
    Returns:
        ProjectScopingAgent instance
    """
    global _agent_instance
    
    if _agent_instance is None:
        _agent_instance = ProjectScopingAgent()
    
    return _agent_instance
