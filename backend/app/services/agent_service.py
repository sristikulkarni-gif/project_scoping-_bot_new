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
        use_cases: Optional[str] = None,
        duration: Optional[str] = None,
        closeout_actuals_context: Optional[str] = None,
        past_proposals_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive project scope using Two-Phase agent reasoning.
        """
        logger.info(f"🚀 Agent generating scope for: {project_name} using Two-Phase Deterministic method")
        
        try:
            # 1. Get rate cards
            rate_cards = await get_rate_cards_async(company_id, db_session)
            rate_cards_str = json.dumps(rate_cards, indent=2)
            
            # --- DETERMINISTIC PRE-EXTRACTION START ---
            rfp_text_normalized = re.sub(r'[^a-z0-9\s]', '', rfp_text.lower())
            tech_aliases = {
                "Azure SQL Database": ["sql db", "azure sql db", "sql database", "azure sql"],
                "Azure Data Lake Storage Gen2": ["adls", "adls gen2", "azure data lake"],
                "Databricks": ["azure databricks"],
                "Power BI": ["powerbi", "power-bi"],
                "Microsoft Azure": ["azure"],
                "React": ["reactjs", "react.js"],
                "Node.js": ["nodejs", "node"],
                "PostgreSQL": ["postgres"],
            }
            
            extracted_explicit_stack = []
            
            for key, aliases in tech_aliases.items():
                key_normalized = re.sub(r'[^a-z0-9\s]', '', key.lower())
                # Check if the key or ANY of its aliases are in the RFP
                if key_normalized in rfp_text_normalized or any(re.sub(r'[^a-z0-9\s]', '', a.lower()) in rfp_text_normalized for a in aliases):
                    extracted_explicit_stack.append(key)
            
            explicit_stack_str = ", ".join(extracted_explicit_stack) if extracted_explicit_stack else "None strictly identified."
            logger.info(f"🔍 Pre-Extracted Explicit Stack: {explicit_stack_str}")
            # --- DETERMINISTIC PRE-EXTRACTION END ---
            
            # 2. Phase 1: High-Level Plan
            plan_prompt = self._build_plan_prompt(
                project_name=project_name, domain=domain, tech_stack=tech_stack,
                rfp_text=rfp_text, explicit_stack_str=explicit_stack_str,
                complexity=complexity, use_cases=use_cases, 
                duration=duration, past_proposals_context=past_proposals_context
            )
            
            logger.info("🤖 Agent starting Phase 1: Planning (Structured Output)...")
            from app.schemas import PlanOutput, ScheduleOutput
            
            plan_llm = self.llm.with_structured_output(PlanOutput)
            plan_result = await plan_llm.ainvoke([
                SystemMessage(content=PROJECT_SCOPING_SYSTEM_PROMPT),
                HumanMessage(content=plan_prompt)
            ])
            
            logger.info(f"✅ Phase 1 Complete. Found {len(plan_result.phases)} phases, {len(plan_result.team_roles)} roles.")
            
            # 3. Phase 2: Granular Schedule (No Dates, Just Dependencies)
            schedule_prompt = self._build_schedule_prompt(
                plan=plan_result, rfp_text=rfp_text, rate_cards=rate_cards_str,
                duration=duration, closeout_actuals_context=closeout_actuals_context,
                past_proposals_context=past_proposals_context
            )
            
            logger.info("🤖 Agent starting Phase 2: Scheduling (Structured Output)...")
            schedule_llm = self.llm.with_structured_output(ScheduleOutput)
            schedule_result = await schedule_llm.ainvoke([
                SystemMessage(content=PROJECT_SCOPING_SYSTEM_PROMPT),
                HumanMessage(content=schedule_prompt)
            ])
            
            logger.info(f"✅ Phase 2 Complete. Generated {len(schedule_result.activities)} granular activities.")
            
            # 4. Construct final raw data package (to be passed to CPM Math in engine)
            # Serialize tech stack categories safely from the new Pydantic schema
            tech_stack_list = []
            
            for cat in getattr(plan_result, 'recommended_tech_stack', []):
                cat_dict = cat.dict() if hasattr(cat, 'dict') else dict(cat)
                
                processed_technologies = []
                for tech_item in cat_dict.get('technologies', []):
                    # tech_item is now a dict with name, classification, justification
                    tech_dict = tech_item if isinstance(tech_item, dict) else tech_item.dict()
                    name = tech_dict.get('name', 'Unknown')
                    classification = tech_dict.get('classification', 'Implicit')
                    
                    if classification.lower() == 'explicit':
                        processed_technologies.append(f"{name} (Explicit from RFP)")
                    else:
                        processed_technologies.append(f"{name} (Implicit required foundation)")
                        
                cat_dict['technologies'] = processed_technologies
                tech_stack_list.append(cat_dict)

            scope_data = {
                "project_overview": {
                    "name": project_name,
                    "domain": domain,
                    "objective": plan_result.executive_summary,
                    "key_deliverables": plan_result.key_deliverables,
                    "complexity": getattr(plan_result, 'complexity', 'Medium'),
                    "complexity_reasoning": getattr(plan_result, 'complexity_reasoning', ''),
                },
                "phases": [{"name": p} for p in plan_result.phases],
                "team_composition": [{"role": r} for r in plan_result.team_roles],
                "activities": [act.dict() for act in schedule_result.activities],
                "recommended_tech_stack": tech_stack_list,
                "_agent_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "agent_version": "2.0-deterministic",
                    "reasoning_steps": 2,
                    "tools_used": ["structured_outputs"]
                }
            }
            
            return scope_data
            
        except Exception as e:
            logger.error(f"❌ Agent scope generation failed: {e}", exc_info=True)
            raise
    
    def _build_plan_prompt(
        self,
        project_name: str,
        domain: str,
        tech_stack: str,
        rfp_text: str,
        complexity: Optional[str],
        use_cases: Optional[str],
        duration: Optional[str],
        explicit_stack_str: str = "None strictly identified.",
        past_proposals_context: Optional[str] = None
    ) -> str:
        """Phase 1: Build prompt to extract high-level plan and team roles."""
        
        prompt = f"""Create a high-level project plan for the following project:

**Project Information:**
- **Name**: {project_name}
- **Domain**: {domain}
"""
        
        if complexity:
            prompt += f"- **Complexity**: {complexity}\n"
        
        if use_cases:
            prompt += f"- **Use Cases**: {use_cases}\n"

        if duration:
            prompt += f"- **Target Duration**: {duration}\n"
        
        prompt += f"""
**RFP Document:**
{rfp_text[:8000]}

**Your Task:**
Based on the RFP and domain, do the following:
1. Extract the optimal high-level phases (e.g., Discovery, Design, Build, QA) and required team roles.

---
**CRITICAL TECHNICAL CONSTRAINTS:**
The client EXPLICITLY requires the following technologies (detected directly from the RFP):

[{explicit_stack_str}]

You MUST build the architecture around these specific tools.
You are NOT allowed to replace or remove them.
All implicit recommendations MUST remain compatible with this ecosystem.
Do NOT introduce unrelated stacks (e.g., MERN, LAMP, Kubernetes, generic SaaS stacks) unless explicitly required by the RFP.
---

2. **Recommend a comprehensive tech stack** organized by category. 
   - Choose technologies that are best-suited for the domain ({domain}) and the requirements in the RFP.
   - Be specific with versions where relevant (e.g., 'React 18', 'Python 3.11', 'PostgreSQL 15').
   - Do NOT use generic names — recommend actual, production-grade technologies.
   - For every technology, include a 1-2 sentence `justification`. If the classification is 'Implicit', you MUST explain exactly why it is required as a foundational piece of the explicit ecosystem.
"""
        if past_proposals_context:
            prompt += f"""
**Calibration References (Past Proposals from our company):**
Here are similar proposals we have done before. Use these as calibration references for determining team size, duration, and project complexity.
{past_proposals_context}
"""
        return prompt

    def _build_schedule_prompt(
        self,
        plan: Any,
        rfp_text: str,
        rate_cards: str,
        duration: Optional[str],
        closeout_actuals_context: Optional[str] = None,
        past_proposals_context: Optional[str] = None
    ) -> str:
        """Phase 2: Build prompt to generate detailed activities with dependencies."""
        
        prompt = f"""You are generating the granular schedule for a project.
You must break the project down into specific activities.

**Approved High-Level Plan:**
- Phases: {', '.join(plan.phases)}
- Approved Team Roles: {', '.join(plan.team_roles)}

**CRITICAL RULES FOR ACTIVITIES:**
1. Every activity MUST belong to one of the Phases listed above.
2. Every activity MUST be owned by one of the Team Roles listed above.
3. Every activity MUST have an `effort_months` estimate (e.g., 0.5 for two weeks, 1.0 for a month).
4. You MUST define `dependencies` for tasks that cannot start until another task finishes. Use the exact `name` of the dependent activity. By default, tasks without dependencies start on Day 1 in parallel.
5. YOU ARE STRICTLY FORBIDDEN FROM GENERATING START OR END DATES. The math will be calculated deterministically later based on your dependencies.

**EFFORT CALIBRATION RULES (follow these strictly for consistent estimates):**
Use these industry-standard effort distribution guidelines when assigning `effort_months`:
- Discovery & Requirements phase: **5–10%** of total estimated project effort
- Architecture & System Design: **10–15%** of total project effort
- Core Development (backend + frontend combined): **40–50%** of total project effort
- Integration & API work: **10–15%** of total project effort
- Testing & QA: **15–20%** of total project effort
- Deployment, DevOps & Handover: **5–10%** of total project effort

For individual activity `effort_months`, use these FIXED reference values based on task type:
- A small focused task (e.g. design one screen, write one API endpoint): **0.25 months**
- A medium feature (e.g. build auth module, design DB schema): **0.5 months**
- A large feature (e.g. full payment integration, reporting module): **1.0 month**
- A complex subsystem (e.g. full data pipeline, multi-step workflow engine): **1.5–2.0 months**

DO NOT deviate from these anchor values without a clear reason stated in comments.
"""

        if closeout_actuals_context:
            prompt += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**🔴 MANDATORY OVERRIDE - ACTUAL DATA FROM PROJECT CLOSEOUT:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This project was PREVIOUSLY COMPLETED. The data below is from REAL execution.
You MUST use these specific actual roles and adapt your activity effort estimates to match the total real effort logged.

{closeout_actuals_context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        prompt += f"""
**Available Rate Cards** (For reference when naming roles):
```json
{rate_cards}
```

**Original RFP Document Fragment:**
{rfp_text[:3000]}

Return the strictly formatted nested list of activities.
"""
        if past_proposals_context:
            prompt += f"""
**Calibration References (Past Proposals from our company):**
Here are similar proposals we have done before. Use these past actuals as a baseline to prevent underestimating effort and roles.
{past_proposals_context}
"""
            
        return prompt
    
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
        domain: str,
        duration: Optional[str] = None
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
        
        # Ensure complexity is present in project_overview, defaulting if not set
        if 'complexity' not in scope_data['project_overview']:
            scope_data['project_overview']['complexity'] = 'Medium' # Default value if not already set

        if 'timeline' not in scope_data:
            # Parse duration string if available (e.g. "5 months" -> 5)
            default_months = 6
            if duration:
                 import re
                 match = re.search(r"(\d+(\.\d+)?)", str(duration))
                 if match:
                     default_months = float(match.group(1))

            scope_data['timeline'] = {
                "total_months": default_months,
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=int(default_months * 30))).strftime("%Y-%m-%d")
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
