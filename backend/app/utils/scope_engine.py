# app/utils/scope_engine.py
from __future__ import annotations
import json, re, logging, math, os, tempfile,anyio,pytesseract, openpyxl,tiktoken, pytz, graphviz,requests
from app import models
from calendar import monthrange
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from pptx import Presentation
from io import BytesIO
from PIL import Image
from app.config.config import QDRANT_COLLECTION
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.utils import azure_blob
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.utils.ai_clients import (
    get_llm_client,
    get_embed_client,
    get_qdrant_client,
    embed_text_ollama,
    get_azure_client,
    get_async_azure_client,
    ollama_chat,
)
from app.services.agent_tools import get_rate_cards_async
from app.engine.diagram_generator import generate_architecture
from app.engine.document_processor import (
    extract_text_from_file,
    extract_text_from_files,
    extract_document_overview
)
from app.engine.prompt_templates import (
    build_questionnaire_prompt,
    build_architecture_prompt
)


logger = logging.getLogger(__name__)

# Init AI services
llm_cfg = get_llm_client()
embed_cfg = get_embed_client()
qdrant = get_qdrant_client()

# Utility function to round effort months to nearest 0.5
def round_to_half(value: float) -> float:
    """Round a number to the nearest 0.5 increment, allowing zero.

    Examples:
        0.0 → 0.0 (zero allowed)
        0.1 → 0.0
        0.3 → 0.5
        1.3 → 1.5
        3.8 → 4.0
        4.1 → 4.0
        2.26 → 2.5
    """
    if value == 0:
        return 0.0  # Allow zero values
    rounded = round(value * 2) / 2
    return max(0.5, rounded)  # Minimum 0.5 only for non-zero values




PROJECTS_BASE = "projects"


# Default Role Rates (USD/month)
ROLE_RATE_MAP: Dict[str, float] = {
    "Backend Developer": 3000.0,
    "Frontend Developer": 2800.0,
    "QA Analyst": 1800.0,
    "QA Engineer": 2000.0,
    "Data Engineer": 2800.0,
    "Data Analyst": 2200.0,
    "Data Architect": 3500.0,
    "UX Designer": 2500.0,
    "UI/UX Designer": 2600.0,
    "Project Manager": 3500.0,
    "Cloud Engineer": 3000.0,
    "BI Developer": 2700.0,
    "DevOps Engineer": 3200.0,
    "Security Administrator": 3000.0,
    "System Administrator": 2800.0,
    "Solution Architect": 4000.0,
    "Unassigned Resource": 2500.0,
}

#  helpers
def _strip_code_fences(s: str) -> str:
    m = re.search(r"```(?:json)?(.*?)```", s, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else s

def _repair_json(text: str) -> str:
    """Attempt to fix common JSON syntax errors."""
    import re

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Fix missing commas between object elements (}{)
    text = re.sub(r'}\s*{', r'},{', text)

    # Fix missing commas between array elements (][)
    text = re.sub(r']\s*\[', r'],[', text)

    # Fix missing commas between object properties (common LLM error)
    # Match: "key": "value"<newline>"nextkey": where comma is missing
    text = re.sub(r'("\s*)\n\s*(")', r'\1,\n\2', text)

    # Fix unquoted keys (capture word followed by colon, add quotes)
    # Only match at start of line or after { or , to avoid false positives
    text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)

    # Fix missing colon between key and value: "key" "value" -> "key": "value"
    # Match quoted key followed by whitespace and quoted value without colon
    text = re.sub(r'("[^"]+")(\s+)("[^"]+"|{|\[)', r'\1:\3', text)

    # Fix missing colon after quoted key: "key"{  -> "key": {
    text = re.sub(r'("[^"]+")(\s*)([{[])', r'\1:\3', text)

    return text


def _normalize_activity_fields(act: dict, activity_id: int) -> dict:
    """
    Normalize activity field names to match expected schema.
    Handles various field name variations from LLM.
    """
    from datetime import datetime, timedelta

    # Map various field name variations to expected field names
    activity_name = (
        act.get('Activities', '') or
        act.get('name', '') or
        act.get('activity', '') or
        act.get('Activity', '')
    )


    owner = (
        act.get('Owner', '') or
        act.get('owner', '') or
        act.get('responsible', '') or
        act.get('assignee', '') or
        "Unassigned Resource"  # Default fallback
    )

    resources = act.get('Resources', '') or act.get('resources', '')
    if isinstance(resources, list):
        resources = ", ".join(resources)

    start_date = (
        act.get('Start Date', '') or
        act.get('start_date', '') or
        act.get('startDate', '')
    )

    end_date = (
        act.get('End Date', '') or
        act.get('end_date', '') or
        act.get('endDate', '')
    )

    # Handle effort/duration in various forms
    effort_months = (
        act.get('Effort Months', 0) or
        act.get('effort_months', 0) or
        act.get('effortMonths', 0) or
        act.get('duration', 0) or
        act.get('story_points', 0) / 20.0  # Convert story points to months (rough estimate)
    )

    if not effort_months or effort_months <= 0:
        effort_months = 1.0

    # Round effort months to nearest 0.5
    effort_months = round_to_half(float(effort_months))

    # If no dates provided, calculate from today
    if not start_date:
        start = datetime.today() + timedelta(days=(activity_id - 1) * 7)
        start_date = start.strftime("%Y-%m-%d")
        end_date = (start + timedelta(days=int(effort_months * 30))).strftime("%Y-%m-%d")

    return {
        "ID": activity_id,
        "Activities": activity_name,
        "Owner": owner,
        "Resources": resources,
        "Start Date": start_date,
        "End Date": end_date,
        "Effort Months": float(effort_months)
    }


    """
    Transform LLM's nested schema (with phases containing activities)
    into the flat schema expected by the backend.

    Handles cases where LLM returns:
    {
      "project": "...",
      "phases": [{..., "activities": [...]}],
      ...
    }

    And converts to:
    {
      "overview": {...},
      "activities": [...],
      "resourcing_plan": []
    }
    """
    # Check if already in flat format but need field normalization
    if raw.get('overview') and raw.get('activities'):
        logger.info("✅ JSON has flat structure, checking field names...")
        # Normalize activity field names even if structure is correct
        activities = raw.get('activities', [])
        if activities and isinstance(activities, list):
            normalized_activities = []
            for idx, act in enumerate(activities, 1):
                if isinstance(act, dict):
                    normalized = _normalize_activity_fields(act, idx)
                    # Check if normalization was needed
                    if 'Activities' not in act or 'Owner' not in act:
                        logger.info(f"🔧 Normalized activity {idx} field names")
                    normalized_activities.append(normalized)
                elif isinstance(act, str):
                    # Handle string activities
                    normalized_activities.append({
                        "ID": idx,
                        "Activities": act,
                        "Owner": "Backend Developer",
                        "Resources": "",
                        "Start Date": "",
                        "End Date": "",
                        "Effort Months": 1.0
                    })

            if normalized_activities:
                raw['activities'] = normalized_activities
                logger.info(f"✅ Normalized {len(normalized_activities)} activities")

        return raw

    # Check if data is wrapped in a "data" key - unwrap it
    if raw.get('data') and isinstance(raw.get('data'), dict):
        logger.info(" Unwrapping nested 'data' key...")
        raw = raw.get('data')

    # Check if it's in nested format (has 'phases' or 'project' at root level, or activities inside)
    if not (raw.get('phases') or raw.get('project') or raw.get('activities')):
        logger.warning("⚠️ JSON format unclear - returning as-is")
        return raw

    logger.info("🔄 Transforming nested JSON schema to flat format...")

    # Helper function to safely extract string values from potentially nested dicts
    def safe_extract(key: str, default=''):
        """Extract value, handling both string and nested dict cases."""
        val = raw.get(key, default)
        if isinstance(val, dict):
            # If it's a dict, try to extract 'name' or the key itself
            return val.get('name', '') or val.get(key, default)
        return val or default

    # Build overview from top-level fields
    # Handle case where 'project' might be a dict with nested fields
    project_val = raw.get('project', '')
    if isinstance(project_val, dict):
        project_name = project_val.get('name', '') or getattr(project, 'name', '')
        logger.info(f"📋 Extracted project name from nested dict: {project_name}")
    else:
        project_name = project_val or getattr(project, 'name', '')

    overview = {
        "Project Name": project_name,
        "Domain": safe_extract('domain', getattr(project, 'domain', '')),
        "Complexity": safe_extract('complexity', getattr(project, 'complexity', '')),
        "Tech Stack": safe_extract('tech_stack', getattr(project, 'tech_stack', '')),
        "Use Cases": safe_extract('use_cases', getattr(project, 'use_cases', '')),
        "Compliance": safe_extract('compliance', getattr(project, 'compliance', '')),
        "Duration": raw.get('duration', 0) or getattr(project, 'duration', 0)
    }

    # Extract and flatten activities
    # Handle both:
    # 1. Activities nested in phases: {"phases": [{"activities": [...]}]}
    # 2. Activities directly in raw: {"activities": [...]}
    activities = []
    activity_id = 1

    # First check if activities are in phases
    phases = raw.get('phases', [])
    if phases:
        for phase in phases:
            phase_name = phase.get('name', 'Unnamed Phase')
            phase_activities = phase.get('activities', [])

            for act in phase_activities:
                # Handle both string and dict activities
                if isinstance(act, str):
                    # Activity is just a string description
                    flat_activity = {
                        "ID": activity_id,
                        "Activities": act,
                        "Owner": "Backend Developer",
                        "Resources": "",
                        "Start Date": "",
                        "End Date": "",
                        "Effort Months": 1.0
                    }
                elif isinstance(act, dict):
                    # Activity is a dict with structured fields
                    flat_activity = {
                        "ID": activity_id,
                        "Activities": act.get('name', '') or act.get('activity', ''),
                        "Owner": act.get('owner', '') or act.get('responsible', '') or "Unassigned Resource",
                        "Resources": ", ".join(act.get('resources', [])) if isinstance(act.get('resources'), list) else act.get('resources', ''),
                        "Start Date": act.get('start_date', '') or act.get('startDate', ''),
                        "End Date": act.get('end_date', '') or act.get('endDate', ''),
                        "Effort Months": act.get('effort_months', 0) or act.get('effortMonths', 0) or 1.0
                    }
                else:
                    # Skip invalid activity types
                    logger.warning(f"⚠️ Skipping invalid activity type: {type(act)}")
                    continue

                # If no start/end dates, calculate from today
                if not flat_activity["Start Date"]:
                    from datetime import datetime, timedelta
                    start = datetime.today() + timedelta(days=(activity_id - 1) * 7)
                    flat_activity["Start Date"] = start.strftime("%Y-%m-%d")
                    flat_activity["End Date"] = (start + timedelta(days=30)).strftime("%Y-%m-%d")
                    flat_activity["Effort Months"] = 1.0

                activities.append(flat_activity)
                activity_id += 1

        logger.info(f"✅ Extracted {len(activities)} activities from {len(phases)} phases")

    # If no phases, check if activities are directly at root level
    elif raw.get('activities'):
        logger.info("📋 Found activities directly at root level")
        for act in raw.get('activities', []):
            # Same handling as above
            if isinstance(act, str):
                flat_activity = {
                    "ID": activity_id,
                    "Activities": act,
                    "Owner": "Unassigned Resource",
                    "Resources": "",
                    "Start Date": "",
                    "End Date": "",
                    "Effort Months": 1.0
                }
            elif isinstance(act, dict):
                flat_activity = {
                    "ID": activity_id,
                    "Activities": act.get('name', '') or act.get('activity', ''),
                    "Owner": act.get('owner', '') or act.get('responsible', '') or "Unassigned Resource",
                    "Resources": ", ".join(act.get('resources', [])) if isinstance(act.get('resources'), list) else act.get('resources', ''),
                    "Start Date": act.get('start_date', '') or act.get('startDate', ''),
                    "End Date": act.get('end_date', '') or act.get('endDate', ''),
                    "Effort Months": act.get('effort_months', 0) or act.get('effortMonths', 0) or 1.0
                }
            else:
                logger.warning(f"⚠️ Skipping invalid activity type: {type(act)}")
                continue

            # If no start/end dates, calculate from today
            if not flat_activity["Start Date"]:
                from datetime import datetime, timedelta
                start = datetime.today() + timedelta(days=(activity_id - 1) * 7)
                flat_activity["Start Date"] = start.strftime("%Y-%m-%d")
                flat_activity["End Date"] = (start + timedelta(days=30)).strftime("%Y-%m-%d")
                flat_activity["Effort Months"] = 1.0

            activities.append(flat_activity)
            activity_id += 1

        logger.info(f"✅ Extracted {len(activities)} activities from root level")

    # Build transformed structure
    transformed = {
        "overview": overview,
        "activities": activities,
        "resourcing_plan": [],  # Will be auto-generated by clean_scope
    }

    # Preserve risks/assumptions if present
    if raw.get('risks'):
        transformed['risks'] = raw.get('risks')
    if raw.get('assumptions'):
        transformed['assumptions'] = raw.get('assumptions')
    if raw.get('project_summary'):
        transformed['project_summary'] = raw.get('project_summary')

    return transformed


def _extract_json(s: str) -> dict:
    raw = _strip_code_fences(s or "")
    try:
        parsed = json.loads(raw.strip())
        # If Ollama returns a list at root level, check if it's activities
        if isinstance(parsed, list):
            logger.warning(f"⚠️  Ollama returned a list instead of dict. Wrapping in activities key.")
            return {"activities": parsed}
        return parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        logger.warning(f"⚠️  First JSON parse attempt failed: {str(e)}")
        logger.warning(f"   Trying to extract JSON from braces...")
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                extracted = raw[start:end+1]
                logger.info(f"   Extracted JSON length: {len(extracted)} chars")
                logger.info(f"   Extracted JSON preview (first 300 chars): {extracted[:300]}")
                logger.info(f"   Extracted JSON ending (last 200 chars): {extracted[-200:]}")
                parsed = json.loads(extracted)
                if isinstance(parsed, list):
                    logger.warning(f"⚠️  Ollama returned a list instead of dict. Wrapping in activities key.")
                    return {"activities": parsed}
                logger.info(f"✅ Successfully parsed JSON with {len(parsed)} top-level keys: {list(parsed.keys())}")
                return parsed if isinstance(parsed, dict) else {}
            except Exception as e2:
                logger.warning(f"⚠️  Second JSON parse attempt also failed: {str(e2)}")
                logger.warning(f"   Attempting JSON repair...")
                try:
                    # Try to repair common JSON syntax errors
                    repaired = _repair_json(extracted)
                    logger.info(f"   Repaired JSON preview (first 300 chars): {repaired[:300]}")
                    logger.info(f"   Repaired JSON ending (last 200 chars): {repaired[-200:]}")
                    parsed = json.loads(repaired)
                    if isinstance(parsed, list):
                        logger.warning(f"⚠️  Ollama returned a list instead of dict. Wrapping in activities key.")
                        return {"activities": parsed}
                    logger.info(f"✅ Successfully parsed repaired JSON with {len(parsed)} top-level keys: {list(parsed.keys())}")
                    return parsed if isinstance(parsed, dict) else {}
                except Exception as e3:
                    logger.error(f"❌ JSON repair also failed: {str(e3)}")
                    logger.error(f"   Raw text length: {len(raw)} chars")
                    logger.error(f"   Raw text preview (first 300 chars): {raw[:300]}")
                    logger.error(f"   Raw text ending (last 200 chars): {raw[-200:]}")
                    return {}
        return {}



def _parse_date_safe(val: Any, fallback: datetime = None) -> datetime:
    """Try to parse a date string; return fallback if invalid."""
    if not val:
        return fallback
    try:
        return datetime.strptime(str(val), "%Y-%m-%d")
    except Exception:
        return fallback

def _safe_str(val: Any) -> str:
    """Convert value to string, handling arrays and dictionaries by joining them."""
    if val is None:
        return ""

    # If it's a dictionary, extract all values and flatten them
    if isinstance(val, dict):
        all_values = []
        for v in val.values():
            if isinstance(v, list):
                all_values.extend(v)
            elif v:
                all_values.append(str(v))
        return ", ".join(str(item).strip() for item in all_values if item)

    # If it's a list/array, join with commas
    if isinstance(val, list):
        return ", ".join(str(item).strip() for item in val if item)

    # Check if it's a string representation of an array like "['item1', 'item2']"
    if isinstance(val, str) and val.strip().startswith('[') and val.strip().endswith(']'):
        try:
            import json
            parsed = json.loads(val.replace("'", '"'))  # Convert single quotes to double quotes for JSON
            if isinstance(parsed, list):
                return ", ".join(str(item).strip() for item in parsed if item)
        except:
            # If JSON parsing fails, try Python literal eval
            try:
                import ast
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return ", ".join(str(item).strip() for item in parsed if item)
            except:
                pass  # If both fail, return as-is below

    # Check if it's a string representation of a dict like "{'key': ['val1', 'val2']}"
    if isinstance(val, str) and val.strip().startswith('{') and val.strip().endswith('}'):
        try:
            import ast
            parsed = ast.literal_eval(val)
            if isinstance(parsed, dict):
                all_values = []
                for v in parsed.values():
                    if isinstance(v, list):
                        all_values.extend(v)
                    elif v:
                        all_values.append(str(v))
                return ", ".join(str(item).strip() for item in all_values if item)
        except:
            pass  # If parsing fails, return as-is below

    return str(val).strip()

async def get_rate_map_for_project(db: AsyncSession, project) -> Dict[str, float]:
    """
    Fetch rate cards for the given project/company.
    Falls back to Sigmoid default rates if none exist
    """
    try:
        # If project has company_id, try fetching company-specific rate cards
        if getattr(project, "company_id", None):
            result = await db.execute(
                select(models.RateCard)
                .filter(models.RateCard.company_id == project.company_id)
            )
            ratecards = result.scalars().all()
            if ratecards:
                return {r.role_name: float(r.monthly_rate) for r in ratecards}

        sigmoid_result = await db.execute(
            select(models.Company).filter(models.Company.name == "Sigmoid")
        )
        sigmoid = sigmoid_result.scalars().first()
        if sigmoid:
            result = await db.execute(
                select(models.RateCard)
                .filter(models.RateCard.company_id == sigmoid.id)
            )
            sigmoid_rates = result.scalars().all()
            if sigmoid_rates:
                return {r.role_name: float(r.monthly_rate) for r in sigmoid_rates}

    except Exception as e:
        logger.warning(f"Failed to fetch rate cards: {e}")
    return ROLE_RATE_MAP



# 👉 It converts the user’s query into an embedding,
# 👉 searches similar document chunks in Qdrant,
# 👉 and returns the most relevant pieces of knowledge.

def _rag_retrieve(query: str, k: int = 5) -> List[Dict]:
    """
    Retrieve semantically similar chunks from Qdrant for RAG.
    Uses embedding model and returns list of matched chunks.
    Skips retrieval if no valid embedding found.
    """
    try:
        q_emb_list = embed_text_ollama([query])

        # Skip if no valid embeddings returned
        if not q_emb_list or not q_emb_list[0]:
            logger.warning("⚠️ No valid embedding generated — skipping Qdrant retrieval.")
            return []

        q_emb = q_emb_list[0]

        # Sanity check vector dimension
        if not isinstance(q_emb, list) or len(q_emb) == 0:
            logger.warning("⚠️ Empty embedding vector — skipping retrieval.")
            return []

        client = get_qdrant_client()
        # Search ONLY in KB collection (case studies are in separate collection)
        # Use query_points instead of deprecated search
        search_result = client.query_points(
            collection_name=QDRANT_COLLECTION,  # KB documents only, no case studies
            query=q_emb,
            limit=k,
            with_payload=True
        )
        results = search_result.points

        logger.info(f"🔍 Searching knowledge base (Qdrant) - found {len(results)} results (KB documents only, excluding case studies)")

        hits = []
        for r in results:
            payload = r.payload or {}
            file_name = payload.get("file_name", "unknown")
            chunk_index = payload.get("chunk_index", "?")
            score = r.score

            # Log each result with details
            logger.info(f"   📄 {file_name} (chunk {chunk_index}): similarity {score:.3f}")

            hits.append({
                "id": payload.get("chunk_id", str(r.id)),
                "parent_id": payload.get("parent_id"),
                "content": payload.get("chunk", ""),
                "title": payload.get("title", ""),
                "score": r.score,
            })

        # Group by parent_id for consistency
        grouped = {}
        for h in hits:
            grouped.setdefault(h["parent_id"], []).append({
                "id": h["id"],
                "content": h["content"],
                "title": h["title"],
                "score": h["score"],
            })

        return [
            {"parent_id": pid, "chunks": chs}
            for pid, chs in grouped.items()
        ]

    except Exception as e:
        logger.warning(f"RAG retrieval (Qdrant) failed: {e}")
        return []

def _retrieve_past_proposals(rfp_text: str, k: int = 3) -> list[dict]:
    """
    Retrieve semantically similar past proposals from Qdrant to use as few-shot calibration examples in prompts.
    """
    try:
        from app.utils.ai_clients import embed_text_azure
        # Embed the query, limit to avoid token limit errors
        q_emb_list = embed_text_azure([rfp_text[:5000]])
        
        if not q_emb_list or not q_emb_list[0]:
            return []
            
        q_emb = q_emb_list[0]
        
        client = get_qdrant_client()
        PAST_PROPOSALS_COLLECTION = os.getenv("PAST_PROPOSALS_COLLECTION", "past_proposals")
        
        search_result = client.query_points(
            collection_name=PAST_PROPOSALS_COLLECTION,
            query=q_emb,
            limit=k,
            with_payload=True
        )
        
        results = []
        for r in search_result.points:
            payload = r.payload or {}
            metadata_str = payload.get("metadata", "{}")
            try:
                metadata = json.loads(metadata_str)
            except Exception:
                metadata = {}
                
            results.append({
                "client_name": metadata.get("client_name", "Unknown"),
                "domain": metadata.get("domain", "Unknown"),
                "duration_months": metadata.get("duration_months", 0),
                "team_size": metadata.get("team_size", 0),
                "total_cost": metadata.get("total_cost", 0),
                "summary": payload.get("chunk", "")
            })
            
        return results
    except Exception as e:
        logger.warning(f"Past proposals retrieval failed: {e}")
        return []



def _extract_questions_from_text(raw_text: str) -> list[dict]:
    try:
        parsed = _extract_json(raw_text)

        # Case 1: Proper JSON with nested categories
        if isinstance(parsed, dict) and "questions" in parsed:
            qdata = parsed["questions"]
            if isinstance(qdata, list) and all(isinstance(x, dict) for x in qdata):
                # check if already nested structure
                if "items" in qdata[0]:
                    normalized = []
                    for cat in qdata:
                        normalized.append({
                            "category": cat.get("category", "General"),
                            "items": [
                                {
                                    "question": i.get("question", ""),
                                    "user_understanding": i.get("user_understanding", ""),
                                    "comment": i.get("comment", "")
                                } for i in cat.get("items", [])
                            ]
                        })
                    return normalized

                # Otherwise, flat → group by category
                grouped = {}
                for q in qdata:
                    cat = q.get("category", "General") if isinstance(q, dict) else "General"
                    que = q.get("question", q) if isinstance(q, dict) else str(q)
                    grouped.setdefault(cat, []).append({
                        "question": que,
                        "user_understanding": "",
                        "comment": ""
                    })
                return [{"category": c, "items": lst} for c, lst in grouped.items()]

        # Case 2: List of plain questions
        if isinstance(parsed, list):
            return [{
                "category": "General",
                "items": [{"question": str(q), "user_understanding": "", "comment": ""} for q in parsed]
            }]
    except Exception:
        pass

    # Fallback to direct regex JSON extraction if _extract_json failed
    try:
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
             potential_json = json.loads(json_match.group(0))
             # If we successfully parsed JSON, recursively call this function or format it
             # For now, let's just see if we can extract questions from it manually
             if "questions" in potential_json and isinstance(potential_json["questions"], list):
                 return _extract_questions_from_text(json.dumps(potential_json)) # Re-process cleanly
    except Exception:
        pass

    # Fallback — parse raw text
    current_cat = "General"
    grouped: dict[str, list] = {}
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^(#+\s*)?([A-Z][A-Za-z\s&/]+):?$", line) and not line.endswith("?"):
            current_cat = re.sub(r"^#+\s*", "", line).strip(": ").strip()
            continue
        if "?" in line:
            qtext = re.sub(r"^\d+[\).\s]+", "", line).strip()
            grouped.setdefault(current_cat, []).append({
                "question": qtext,
                "user_understanding": "",
                "comment": ""
            })

    return [{"category": c, "items": lst} for c, lst in grouped.items()]



def _retrieve_relevant_sections_by_aspects(project_name: str, aspects: List[str], k: int = 2) -> List[str]:
    """
    Use RAG to retrieve relevant document sections for specific aspects.
    This ensures we get focused content instead of entire document.

    Args:
        project_name: Name of the project for contextual queries
        aspects: List of aspects to query (e.g., "technical requirements")
        k: Number of chunks to retrieve per aspect

    Returns:
        List of relevant text sections
    """
    relevant_sections = []

    for aspect in aspects:
        try:
            # Create focused query
            query = f"{project_name} {aspect}"

            # Use existing RAG retrieval
            results = _rag_retrieve(query, k=k)

            if results:
                # Extract text chunks
                for group in results:
                    for chunk in group.get("chunks", []):
                        content = chunk.get("content", "")
                        if content and content not in relevant_sections:  # Avoid duplicates
                            relevant_sections.append(content)
        except Exception as e:
            logger.warning(f"Failed to retrieve sections for aspect '{aspect}': {e}")
            continue

    return relevant_sections

async def generate_project_questions(db: AsyncSession, project) -> dict:
    """
    Generate a categorized questionnaire for the given project using Ollama.
    Saves the questions.json file in Azure Blob.
    """

    # ---------- Extract RFP ----------
    rfp_text = ""
    try:
        if getattr(project, "files", None):
            files = [{"file_name": f.file_name, "file_path": f.file_path} for f in project.files]
            if files:
                rfp_text = await extract_text_from_files(files)
    except Exception as e:
        logger.warning(f"Failed to extract RFP for questions: {e}")

    # ---------- Smart Document Processing (Chunked RAG Approach) ----------
    # Instead of sending entire large document, use overview + RAG-retrieved sections
    focused_rfp_content = ""

    if rfp_text:
        # Extract document overview (first ~2500 words) instead of entire document
        rfp_overview = extract_document_overview(rfp_text, max_chars=10000)
        logger.info(f"📄 Extracted RFP overview: {len(rfp_overview)} chars (from {len(rfp_text)} total chars)")

        # Define key aspects to query for relevant sections
        key_aspects = [
            "technical requirements and specifications",
            "project scope and deliverables",
            "timeline and milestones",
            "budget and resource constraints",
            "integration and compatibility requirements",
            "security and compliance requirements"
        ]

        # Use RAG to retrieve relevant sections for each aspect
        project_name = getattr(project, "name", None) or getattr(project, "domain", None) or "project"
        relevant_sections = _retrieve_relevant_sections_by_aspects(project_name, key_aspects, k=2)

        if relevant_sections:
            logger.info(f"🔍 Retrieved {len(relevant_sections)} relevant sections via RAG")

        # Combine overview + relevant sections (focused content, not full document)
        focused_rfp_content = rfp_overview
        if relevant_sections:
            # Limit to 10 sections to avoid overwhelming the prompt
            focused_rfp_content += "\n\n=== Additional Relevant Details ===\n\n"
            focused_rfp_content += "\n\n".join(relevant_sections[:10])

        logger.info(f"✅ Using focused content: {len(focused_rfp_content)} chars (reduced from {len(rfp_text)} chars)")
    else:
        # No RFP files, use project metadata
        focused_rfp_content = rfp_text

    # ---------- Retrieve Knowledge Base ----------
    kb_query = focused_rfp_content or project.name or project.domain
    kb_results = _rag_retrieve(kb_query)
    kb_chunks = [ch["content"] for group in kb_results for ch in group["chunks"]][:5] if kb_results else []

    # ---------- Build prompt with focused content ----------
    prompt = build_questionnaire_prompt(focused_rfp_content, kb_chunks, project)

    # ---------- Query Ollama ----------
    try:
        raw_text = await anyio.to_thread.run_sync(
            lambda: ollama_chat(prompt, temperature=0.7, format_json=True)
        )
        logger.error(f"DEBUG - RAW QUESTIONS OUTPUT: {raw_text[:1000]}...") # Debug log
        questions = _extract_questions_from_text(raw_text)
        total_q = sum(len(cat["items"]) for cat in questions)
        logger.info(f" Generated {total_q} questions under {len(questions)} categories for project {project.id}")

        # ---------- Save to Blob Storage ----------
        blob_name = f"{PROJECTS_BASE}/{project.id}/questions.json"
        try:
            await azure_blob.upload_bytes(
                json.dumps({"questions": questions}, ensure_ascii=False, indent=2).encode("utf-8"),
                blob_name,
            )

            db_file = models.ProjectFile(
                project_id=project.id,
                file_name="questions.json",
                file_path=blob_name,
            )

            db.add(db_file)
            await db.commit()
            await db.refresh(db_file)

            logger.info(f" Saved questions.json for project {project.id}")
        except Exception as e:
            logger.warning(f"Failed to upload questions.json: {e}")

        return {"questions": questions}

    except Exception as e:
        logger.error(f" Question generation failed: {e}")
        return {"questions": []}
    
# Update questions.json with user input answers
async def update_questions_with_user_input(
    db: AsyncSession, project, user_answers: dict
) -> dict:
    from app.utils import azure_blob

    blob_name = f"{PROJECTS_BASE}/{project.id}/questions.json"
    try:
        # Load current questions.json
        q_bytes = await azure_blob.download_bytes(blob_name)
        q_json = json.loads(q_bytes.decode("utf-8"))
        questions = q_json.get("questions", [])

        # Merge answers into the structure
        for cat in questions:
            cat_name = cat.get("category")
            for item in cat.get("items", []):
                q_text = item.get("question")
                ans = (
                    user_answers.get(cat_name, {}).get(q_text)
                    if user_answers.get(cat_name)
                    else None
                )
                if ans:
                    item["user_understanding"] = ans

        # Upload updated JSON to Blob
        new_bytes = json.dumps({"questions": questions}, ensure_ascii=False, indent=2).encode("utf-8")
        await azure_blob.upload_bytes(new_bytes, blob_name)
        logger.info(f" Updated questions.json with user input for project {project.id}")

        #  Save / update DB record
        db_file = models.ProjectFile(
            project_id=project.id,
            file_name="questions.json",
            file_path=blob_name,
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        return {"questions": questions}

    except Exception as e:
        logger.error(f"Failed to update questions.json with user input: {e}")
        return {}

    







# --- Cleaner ---
async def clean_scope(db: AsyncSession, data: Dict[str, Any], project=None) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    ist = pytz.timezone("Asia/Kolkata")
    # Use timezone-naive datetime to avoid comparison issues with parsed dates
    today = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    activities: List[Dict[str, Any]] = []
    start_dates, end_dates = [], []
    role_month_map: Dict[str, Dict[str, float]] = {}
    role_order: List[str] = []

    # --- Fetch Valid Roles Dynamically from DB ---
    valid_role_keywords = ["developer", "engineer", "architect", "analyst", "designer", "lead", "manager", "tester", "qa", "owner", "admin", "consultant", "specialist"]
    try:
        company_id = getattr(project, "company_id", None)
        if company_id:
            logger.info(f"Fetching dynamic roles for company {company_id}...")
            rate_cards = await get_rate_cards_async(str(company_id), db)
            if rate_cards:
                # Add roles from DB to our whitelist
                db_roles = [r.lower() for r in rate_cards.keys()]
                # Extract unique keywords from DB roles (e.g. "Backend Developer" -> "backend", "developer")
                # Or just add the full role names? 
                # Better to keep the keyword approach for flexibility (e.g. "Senior Backend Developer" matches "developer")
                # But we can also add the full strings to be safe.
                for r in db_roles:
                   parts = r.split()
                   valid_role_keywords.extend(parts)
                
                # Deduplicate
                valid_role_keywords = list(set(valid_role_keywords))
                logger.info(f"✅ Dynamic Role Whitelist: {len(valid_role_keywords)} keywords")
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch dynamic roles, using defaults: {e}")

    # --- Helper: compute monthly allocation based on actual days in month ---
    def month_effort(s: datetime, e: datetime) -> Dict[str, float]:
        cur = s
        month_eff = {}
        while cur <= e:
            year, month = cur.year, cur.month
            days_in_month = monthrange(year, month)[1]
            start_day = cur.day if cur.month == s.month else 1
            end_day = e.day if cur.month == e.month else days_in_month
            days_count = end_day - start_day + 1
            month_eff[f"{cur.strftime('%b %Y')}"] = round(days_count / 30.0, 2)
            # move to next month
            if month == 12:
                cur = datetime(year + 1, 1, 1)
            else:
                cur = datetime(cur.year, cur.month + 1, 1)
        return month_eff

    # --- NEW: Rescale activities if duration differs significantly from project.duration ---
    target_months = 0.0
    try:
        # 1. Parse target duration from project metadata
        # Handle project duration (e.g. "7 months", "6", "approx 7")
        raw_duration = str(getattr(project, "duration", "") or "").lower().strip()
        
        # If not in project, check if it's in the data['overview']
        if not raw_duration and data.get("overview"):
            raw_duration = str(data.get("overview", {}).get("Duration", "") or "").lower().strip()
            
        if raw_duration:
            # Extract first number found
            match = re.search(r"(\d+(\.\d+)?)", raw_duration)
            if match:
                target_months = float(match.group(1))
                
        # 2. Calculate current inferred duration from activities
        # Check if AI explicitly recommended a different duration based on actuals
        ai_duration_str = str(data.get("ai_recommended_duration", "")).lower().strip()
        if ai_duration_str:
            ai_match = re.search(r"(\d+(\.\d+)?)", ai_duration_str)
            if ai_match:
                ai_months = float(ai_match.group(1))
                if ai_months > 0 and abs(ai_months - target_months) > 0.5:
                     logger.info(f"🤖 AI recommended duration {ai_months} differs from target {target_months}. Respecting AI (Actual Data).")
                     target_months = ai_months

        if target_months > 0 and data.get("activities"):
            temp_starts = []
            temp_ends = []
            valid_acts = []
            
            for a in data.get("activities", []):
                s_date = _parse_date_safe(a.get("Start Date"), today)
                # If end date is missing or invalid, assume 1 month
                e_date_raw = a.get("End Date")
                if not e_date_raw:
                    e_date = s_date + timedelta(days=30)
                else:
                    e_date = _parse_date_safe(e_date_raw, s_date + timedelta(days=30))
                
                if e_date < s_date:
                    e_date = s_date + timedelta(days=30)
                    
                temp_starts.append(s_date)
                temp_ends.append(e_date)
                valid_acts.append({
                    "act": a, 
                    "s": s_date, 
                    "e": e_date, 
                    "duration_days": (e_date - s_date).days
                })
            
            # Filter out generic default dates if possible, but for now just use all
            if temp_starts and temp_ends:
                min_s = min(temp_starts)
                max_e = max(temp_ends)
                current_days = (max_e - min_s).days
                current_months = current_days / 30.0
                
                # 3. Check if rescaling is needed (allow 10% tolerance)
                diff = abs(current_months - target_months)
                logger.info(f"⚖️ Duration Check: User wants {target_months} months, Scope is {current_months:.2f} months. Diff: {diff:.2f}")

                if current_months > 0 and diff / max(current_months, 1.0) > 0.1:
                    logger.info(f"⚡ RESCALING TRIGGERED: {current_months:.2f} -> {target_months:.2f} (Ratio: {target_months/current_months:.4f})")
                    ratio = target_months / current_months
                    
                    # Apply scaling
                    for item in valid_acts:
                        act = item["act"]
                        # Use start date of the item to offset correctly
                        offset_days = (item["s"] - min_s).days
                        new_offset_days = int(offset_days * ratio)
                        
                        # Calculate new duration
                        old_duration = item["duration_days"]
                        new_duration_days = max(1, int(old_duration * ratio))
                        
                        # Set new dates
                        new_s = min_s + timedelta(days=new_offset_days)
                        new_e = new_s + timedelta(days=new_duration_days)
                        
                        # Update activity in place
                        act["Start Date"] = new_s.strftime("%Y-%m-%d")
                        act["End Date"] = new_e.strftime("%Y-%m-%d")
                        # Update effort estimate too
                        act["Effort Months"] = round_to_half(new_duration_days / 30.0)
                        
    except Exception as e:
        logger.warning(f"⚠️ Failed to rescale project duration: {e}")

    # --- Build list of activity names to filter out from Resources ---
    activity_names = set()
    for a in data.get("activities") or []:
        activity_name = a.get("Activities", "").strip()
        if activity_name:
            activity_names.add(activity_name)

    # --- Process activities ---
    for idx, a in enumerate(data.get("activities") or [], start=1):
        owner = a.get("Owner") or "Unassigned"

        # Parse dependencies
        raw_deps_list = [d.strip() for d in str(a.get("Resources") or "").split(",") if d.strip()]

        # Remove owner from resources if duplicated
        raw_deps_list = [r for r in raw_deps_list if r.lower() != owner.lower()]

        # Strict filtering for Activity Breakdown (matches Resource Plan logic)
        
        # Use the dynamic whitelist we fetched at the start of the function
        # valid_role_keywords is already populated with DB roles + defaults
        
        raw_deps = []
        for r in raw_deps_list:
            r_clean = r.strip()
            r_lower = r_clean.lower()
            
            # 1. Component/Activity name filter
            if r_clean in activity_names:
                continue
            
            # 2. Length check: Too short or too long
            if len(r_clean) < 3 or len(r_clean) > 35:
                continue
                
            # 3. Parentheses filter
            if "(" in r_clean or ")" in r_clean:
                continue
                
            # 4. STRICT WHITELIST: Must contain at least one valid role keyword
            if not any(keyword in r_lower for keyword in valid_role_keywords):
                continue
                
             # 5. Final Sanity Check
            if r_lower in ["system", "implementation", "design", "testing", "analysis", "tasks"]:
                 continue

            raw_deps.append(r_clean)

        # Owner always included, then other resources
        roles = [owner] + raw_deps

        s = _parse_date_safe(a.get("Start Date"), today)
        e = _parse_date_safe(a.get("End Date"), s + timedelta(days=30))
        if e < s:
            e = s + timedelta(days=30)

        # --- allocate per month (no splitting among roles) ---
        month_alloc = month_effort(s, e)
        for role in roles:
            if role not in role_month_map:
                role_month_map[role] = {}
                role_order.append(role)
            for m, eff in month_alloc.items():
                role_month_map[role][m] = role_month_map[role].get(m, 0.0) + eff

        dur_days = max(1, (e - s).days)

        # Clean up activity name: remove seniority indicators
        activity_name = _safe_str(a.get("Activities"))
        # Remove common seniority markers (case-insensitive)
        # Remove common seniority markers (case-insensitive)
        activity_name = re.sub(r'\s*\((Junior|Senior|Mid-?level|Lead)\)\s*', '', activity_name, flags=re.IGNORECASE)
        activity_name = re.sub(r'\s*\-(Junior|Senior|Mid-?level|Lead)\s*', '', activity_name, flags=re.IGNORECASE)
        activity_name = activity_name.strip()

        # --- NEW: Fix Vague Activity Names ---
        # If activity is too generic, append context
        generic_terms = ["frontend development", "backend development", "full stack development", "development", "implementation", "testing", "qa", "design"]
        if activity_name.lower() in generic_terms:
            # Try to add context from phase or tech stack
            # For now, just append "Implementation" or "Execution" to make it slightly better, 
            # but ideally the specific feature name should be used. 
            # We can also append the Tech Stack if available in the overview to make it specific e.g. "React Frontend Development"
            
            tech_context = ""
            if "frontend" in activity_name.lower():
                tech_context = "UI/UX "
            elif "backend" in activity_name.lower():
                tech_context = "API & Logic "
            elif "database" in activity_name.lower():
                tech_context = "Schema "
            
            activity_name = f"{tech_context}{activity_name} - Feature Implementation"
        
        # Ensure it's not just "Phase 1" etc
        if re.match(r'^Phase \d+$', activity_name, re.IGNORECASE):
             activity_name = f"{activity_name} Implementation"

        activities.append({
            "ID": idx,
            "Activities": activity_name,
            "Phase": a.get("Phase", ""),
            "Owner": owner,
            "Resources": ", ".join(raw_deps),
            "Start Date": s,
            "End Date": e,
            "Effort Months": round_to_half(dur_days / 30.0),  # Round to nearest 0.5
        })

        start_dates.append(s)
        end_dates.append(e)

        # --- Sort activities ---
    activities.sort(key=lambda x: x["Start Date"])
    for idx, a in enumerate(activities, start=1):
        a["ID"] = idx
        a["Start Date"] = a["Start Date"].strftime("%Y-%m-%d")
        a["End Date"] = a["End Date"].strftime("%Y-%m-%d")

    # --- Project span & month labels (Month 1, Month 2, ...) ---
    min_start = min(start_dates) if start_dates else today
    max_end = max(end_dates) if end_dates else min_start
    
    # 🧠 PRESERVE CPM MATH DURATION IF AVAILABLE (Unless explicitly regenerating)
    precalculated_duration = data.get("overview", {}).get("Duration")
    force_recalc = data.get("_force_duration_recalc", False)
    
    if precalculated_duration and precalculated_duration != "0 months" and not force_recalc:
        duration = precalculated_duration
        # Extract numerical months for the loop
        match = re.search(r"(\d+(\.\d+)?)", str(duration))
        total_months = max(1, math.ceil(float(match.group(1)))) if match else 1
    else:
        duration_days = (max_end - min_start).days
        total_months_full = int(duration_days / 30)
        remaining_days = duration_days % 30
        
        if total_months_full == 0:
            if remaining_days == 0:
                formatted_duration = "1 day" # Minimum
            else:
                formatted_duration = f"{remaining_days} days"
        else:
            month_str = "month" if total_months_full == 1 else "months"
            if remaining_days <= 1: # Ignore negligible days
                formatted_duration = f"{total_months_full} {month_str}"
            elif remaining_days > 20: # Round up
                formatted_duration = f"{total_months_full + 1} months"
            else:
                formatted_duration = f"{total_months_full} {month_str}, {remaining_days} days"

        duration = formatted_duration
        total_months = max(1, math.ceil(duration_days / 30.0))

    month_labels = [f"Month {i}" for i in range(1, total_months + 1)]

    # --- Build per-role, per-month day usage ---
    role_month_usage: Dict[str, Dict[str, float]] = {r: {m: 0.0 for m in month_labels} for r in role_order}

    # Compute total active days per relative month window
    for act in activities:
        s = _parse_date_safe(act.get("Start Date"), today)
        e = _parse_date_safe(act.get("End Date"), s + timedelta(days=30))
        if e < s:
            e = s + timedelta(days=30)

        # Parse resources and filter out activity names
        # Parse resources and filter out activity names
        # Strict filtering to prevent pollution
        raw_resources = [r.strip() for r in str(act.get("Resources") or "").split(",") if r.strip()]
        resources_list = []
        
        # Strict filtering with Whitelist + Blacklist
        # We only want REAL roles like "Backend Developer", "QA Engineer"
        # We use the dynamic whitelist "valid_role_keywords" from the top of the function
        
        for r in raw_resources:
            r_clean = r.strip()
            r_lower = r_clean.lower()
            
            # 1. Length check: Too short or too long
            if len(r_clean) < 3 or len(r_clean) > 35:
                continue
            
            # 2. Activity / Description check (parentheses)
            if "(" in r_clean or ")" in r_clean:
                continue
                
            # 3. STRICT WHITELIST: Must contain at least one valid role keyword
            # This kills "System", "Implementation", "imps", "rigs" instantly
            if not any(keyword in r_lower for keyword in valid_role_keywords):
                continue
             
            # 4. Final Sanity Check: specific garbage terms that might sneak in
            if r_lower in ["system", "implementation", "design", "testing", "analysis", "tasks"]:
                 continue

            resources_list.append(r_clean)

        involved_roles = [act.get("Owner") or "Unassigned"] + resources_list

        for m_idx in range(total_months):
            rel_start = min_start + timedelta(days=m_idx * 30)
            rel_end = min_start + timedelta(days=(m_idx + 1) * 30)

            # overlap between activity and this relative month window
            overlap_start = max(s, rel_start)
            overlap_end = min(e, rel_end)
            overlap_days = 0
            if overlap_end >= overlap_start:
                overlap_days = (overlap_end - overlap_start).days + 1

            if overlap_days > 0:
                for r in involved_roles:
                    if r not in role_month_usage:
                        role_month_usage[r] = {ml: 0.0 for ml in month_labels}
                    role_month_usage[r][f"Month {m_idx + 1}"] += overlap_days

    # --- Convert days to effort with 4-tier partial-month logic ---
    for r, months in role_month_usage.items():
        for m, days in months.items():
            if days > 21:
                months[m] = 1.0
            elif 15 <= days <= 21:
                months[m] = 0.75
            elif 8 <= days < 15:
                months[m] = 0.5
            elif 1 <= days < 8:
                months[m] = 0.25
            else:
                months[m] = 0.0

    try:
        if db:
            ROLE_RATE_MAP_DYNAMIC = await get_rate_map_for_project(db, project)
        else:
            ROLE_RATE_MAP_DYNAMIC = ROLE_RATE_MAP
    except Exception as e:
        logger.warning(f"Rate map fallback due to error: {e}")
        ROLE_RATE_MAP_DYNAMIC = ROLE_RATE_MAP


    # --- Build final resourcing plan ---
    resourcing_plan = []
    for idx, role in enumerate(role_order, start=1):
        # Round each month's effort to nearest 0.5
        month_efforts_raw = role_month_usage.get(role, {m: 0 for m in month_labels})
        month_efforts = {m: round_to_half(float(v)) for m, v in month_efforts_raw.items()}

        # Calculate and round total effort
        total_effort = round_to_half(sum(month_efforts.values()))

        rate = ROLE_RATE_MAP_DYNAMIC.get(role, ROLE_RATE_MAP.get(role, 2000.0))
        cost = round(total_effort * rate, 2)
        plan_entry = {
            "ID": idx,
            "Resources": role,
            "Rate/month": rate,
            **month_efforts,
            "Efforts": total_effort,
            "Cost": cost,
        }
        resourcing_plan.append(plan_entry)

    # --- Apply discount if present ---
    discount_percentage = data.get("discount_percentage", 0)
    if discount_percentage and isinstance(discount_percentage, (int, float)) and discount_percentage > 0:
        discount_multiplier = 1 - (discount_percentage / 100.0)
        logger.info(f"💰 Applying {discount_percentage}% discount (multiplier: {discount_multiplier})")

        # Apply discount to all costs in resourcing_plan
        for plan_entry in resourcing_plan:
            original_cost = plan_entry.get("Cost", 0)
            discounted_cost = round(original_cost * discount_multiplier, 2)
            plan_entry["Cost"] = discounted_cost
            logger.info(f"  → {plan_entry['Resources']}: ${original_cost} → ${discounted_cost}")

    # --- Overview ---
    ov = data.get("overview") or {}
    data["overview"] = {
        "Project Name": _safe_str(ov.get("Project Name") or getattr(project, "name", "Untitled Project")),
        "Domain": _safe_str(ov.get("Domain") or getattr(project, "domain", "")),
        "Complexity": _safe_str(ov.get("Complexity") or getattr(project, "complexity", "")),
        "Tech Stack": _safe_str(ov.get("Tech Stack") or getattr(project, "tech_stack", "")),
        "Use Cases": _safe_str(ov.get("Use Cases") or getattr(project, "use_cases", "")),
        "Compliance": _safe_str(ov.get("Compliance") or getattr(project, "compliance", "")),
        "Duration": duration,
        "Start Date": _safe_str(ov.get("Start Date") or ""),
        "End Date": _safe_str(ov.get("End Date") or ""),
        "Generated At": datetime.now(ist).strftime("%Y-%m-%d %H:%M %Z"),
    }
    try:
        if getattr(project, "company", None):
            data["overview"]["Currency"] = getattr(project.company, "currency", "USD")
        else:
            data["overview"]["Currency"] = "USD"
    except Exception:
        data["overview"]["Currency"] = "USD"

    # Add discount to overview if present
    if discount_percentage and isinstance(discount_percentage, (int, float)) and discount_percentage > 0:
        data["overview"]["Discount"] = f"{discount_percentage}%"
        total_cost = sum(plan_entry.get("Cost", 0) for plan_entry in resourcing_plan)
        data["overview"]["Total Cost (After Discount)"] = f"${total_cost:,.2f}"

    data["activities"] = activities
    data["resourcing_plan"] = resourcing_plan

    # Keep discount_percentage in output for reference
    if discount_percentage and isinstance(discount_percentage, (int, float)) and discount_percentage > 0:
        data["discount_percentage"] = discount_percentage

    return data


def _transform_agent_output_to_scope_format(agent_scope: dict, project) -> dict:
    """
    Transform agent output format to the legacy scope format expected by clean_scope().
    
    Agent returns:
    {
        "project_overview": {...},
        "phases": [...],
        "team_composition": [...],
        "activities": [...] # raw dictionaries from Pydantic
    }
    """
    from datetime import datetime
    from app.utils.scheduling import calculate_project_schedule
    from app.schemas import ActivityItem
    
    # Build overview
    project_overview = agent_scope.get("project_overview", {})
    
    # Extract AI-generated tech stack to a readable string
    raw_tech_stack = agent_scope.get("recommended_tech_stack", [])
    formatted_tech_stack = ""
    if raw_tech_stack:
        parts = []
        for cat in raw_tech_stack:
            cat_name = cat.get("category", "")
            techs = cat.get("technologies", [])
            if cat_name and techs:
                parts.append(f"{cat_name}: {', '.join(techs)}")
        if parts:
            formatted_tech_stack = " | ".join(parts)
            
    # Default back to the project's tech stack if the generation failed
    final_tech_stack_str = formatted_tech_stack if formatted_tech_stack else getattr(project, "tech_stack", "")

    overview = {
        "Project Name": project_overview.get("name", getattr(project, "name", "Untitled")),
        "Domain": project_overview.get("domain", getattr(project, "domain", "")),
        "Tech Stack": final_tech_stack_str,
        "Use Cases": getattr(project, "use_cases", ""),
        "Complexity": project_overview.get("complexity") or getattr(project, "complexity", ""),
        "Compliance": getattr(project, "compliance", ""),
    }
    
    # Parse activities back into ActivityItem objects to pass into the Scheduler
    raw_activities = agent_scope.get("activities", [])
    activity_items = []
    for act in raw_activities:
        # Provide fallback values if Pydantic schema keys aren't an exact match (safety net)
        activity_items.append(ActivityItem(
            name=act.get("name", "Unnamed Activity"),
            phase=act.get("phase", "Execution"),
            owner=act.get("owner", "Project Manager"),
            effort_months=float(act.get("effort_months", 1.0)),
            dependencies=act.get("dependencies", [])
        ))

    # Assume project starts today
    start_date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 🧠 PASS INTO CPM DETERMINISTIC ALGORITHM
    if activity_items:
        schedule_result = calculate_project_schedule(activity_items, start_date_str)
        activities = schedule_result["activities"]
        overview["Duration"] = f"{schedule_result['total_duration_months']} months"
        overview["Start Date"] = schedule_result["start_date"]
        overview["End Date"] = schedule_result["end_date"]
        logger.info(f"📅 Timeline calculated: {overview['Start Date']} to {overview['End Date']} ({schedule_result['total_duration_months']} months)")
    else:
        activities = []
        overview["Duration"] = "0 months"

    # Build final scope structure
    scope = {
        "overview": overview,
        "activities": activities,
        "project_summary": {
            "executive_summary": project_overview.get("objective", ""),
            "key_deliverables": project_overview.get("key_deliverables", [])
        },
        "recommended_tech_stack": agent_scope.get("recommended_tech_stack", []),
    }

    return scope




def _apply_closeout_actuals_to_scope(scope: dict, resource_actuals) -> dict:
    """
    Post-process a generated scope to override the resourcing plan
    with actual effort/cost data from a previous closeout.
    This ensures regenerated scopes reflect real-world performance.
    """
    logger.info(f"🔴 _apply_closeout_actuals_to_scope called with {len(resource_actuals)} actuals")
    resourcing_plan = scope.get("resourcing_plan", [])
    if not resourcing_plan or not resource_actuals:
        logger.warning(f"🔴 SKIPPING closeout override: resourcing_plan={len(resourcing_plan)}, resource_actuals={len(resource_actuals) if resource_actuals else 0}")
        return scope

    # Build lookup: resource_name -> actual data
    actuals_map = {}
    for ra in resource_actuals:
        key = ra.resource_name.strip().lower()
        actuals_map[key] = ra
        logger.info(f"🔴 Actuals map key: '{key}' -> actual_effort={ra.actual_effort_months}")

    total_cost = 0.0
    max_effort = 0.0

    for plan_entry in resourcing_plan:
        resource_name = plan_entry.get("Resources", "").strip()
        lookup_key = resource_name.lower()
        ra = actuals_map.get(lookup_key)
        logger.info(f"🔴 Plan entry: '{resource_name}' (lookup='{lookup_key}'), match={'YES' if ra else 'NO'}, current_effort={plan_entry.get('Efforts', 0)}")

        if ra:
            old_effort = plan_entry.get("Efforts", 0)
            actual_effort = ra.actual_effort_months
            rate = plan_entry.get("Rate/month", ra.rate_per_month)

            # Scale monthly allocations proportionally
            if old_effort > 0 and actual_effort != old_effort:
                scale_factor = actual_effort / old_effort
                for key in list(plan_entry.keys()):
                    if key not in ("ID", "Resources", "Rate/month", "Efforts", "Cost"):
                        # These are month columns (e.g., "Feb 2026", "Mar 2026")
                        old_val = plan_entry[key]
                        if isinstance(old_val, (int, float)):
                            plan_entry[key] = round(old_val * scale_factor * 2) / 2  # Round to 0.5

            plan_entry["Efforts"] = actual_effort
            plan_entry["Cost"] = round(actual_effort * rate, 2)

            logger.info(f"Closeout override: {resource_name} effort {old_effort} -> {actual_effort} months")

        total_cost += plan_entry.get("Cost", 0)
        max_effort = max(max_effort, plan_entry.get("Efforts", 0))

    # Update overview duration if actuals imply longer project
    overview = scope.get("overview", {})
    old_duration_str = str(overview.get("Duration", ""))
    old_duration_match = re.search(r"(\d+(\.\d+)?)", old_duration_str)
    old_duration = float(old_duration_match.group(1)) if old_duration_match else 0

    if max_effort > old_duration:
        overview["Duration"] = f"{max_effort} months"
        logger.info(f"Closeout override: Duration {old_duration} -> {max_effort} months")

    scope["resourcing_plan"] = resourcing_plan
    scope["overview"] = overview

    logger.info(f"Applied closeout actuals: total_cost=${total_cost:,.2f}, max_effort={max_effort}")
    return scope


async def generate_project_scope(db: AsyncSession, project) -> dict:
    """
    Generate project scope + architecture diagram + store architecture in DB + return combined JSON.
    """

    #  Ensure the project has a valid company reference (fallback to Sigmoid)
    if not getattr(project, "company_id", None):
        from app.utils import ratecards
        sigmoid = await ratecards.get_or_create_sigmoid_company(db)
        project.company_id = sigmoid.id
        await db.commit()
        await db.refresh(project)
        logger.info(f"Linked project {project.id} to Sigmoid company as fallback")

    tokenizer = tiktoken.get_encoding("cl100k_base")
    context_limit = 128000
    max_total_tokens = context_limit - 4000
    used_tokens = 0

    # ---------- Extract RFP ----------
    rfp_text = ""
    try:
        files: List[dict] = []
        if getattr(project, "files", None):
            try:
                files = [{"file_name": f.file_name, "file_path": f.file_path} for f in project.files]
            except Exception as e:
                logger.warning(f" Could not access project.files: {e}")
                files = []
        if files:
            rfp_text = await extract_text_from_files(files)
    except Exception as e:
        logger.warning(f"File extraction for project {getattr(project, 'id', None)} failed: {e}")

    # ---------- Smart Document Processing (Head + Tail + RAG) ----------
    focused_rfp_content = rfp_text
    if rfp_text:
        # If document is under 100,000 tokens, just use the entire complete document for 100% accuracy
        rfp_token_length = len(tokenizer.encode(rfp_text or ""))
        if rfp_token_length <= 100000:
            focused_rfp_content = rfp_text
            logger.info(f"📄 Using full RFP text ({rfp_token_length} tokens) for maximum accuracy")
        else:
            logger.info("🔍 Large document detected. Using Head + Tail + Targeted RAG Extraction.")
            
            # Extract Head (approx 3000 tokens)
            head_text = extract_document_overview(rfp_text, max_chars=12000)
            
            # Extract Tail (approx 2000 tokens from the end)
            tail_chars = 8000
            tail_text = rfp_text[-tail_chars:]
            # Try to cut at a sentence boundary cleanly
            first_period = tail_text.find('. ')
            if first_period != -1 and first_period < tail_chars * 0.2:
                tail_text = tail_text[first_period + 2:]
                
            # Extract Middle using RAG
            project_name = getattr(project, "name", None) or getattr(project, "domain", None) or "project"
            key_aspects = [
                "technical stack architecture infrastructure technologies database frameworks",
                "project phases milestones timeline schedule deliverables",
                "team sizes roles responsibilities resource requirements"
            ]
            relevant_sections = _retrieve_relevant_sections_by_aspects(project_name, key_aspects, k=2)
            
            # Combine everything intelligently
            combined_parts = [
                f"--- EXECUTIVE SUMMARY (START OF RFP) ---\n{head_text}",
            ]
            
            if relevant_sections:
                combined_parts.append("\n--- KEY SCOPING REQUIREMENTS (EXTRACTED) ---")
                combined_parts.append("\n\n".join(relevant_sections))
                
            combined_parts.append(f"\n--- ADDITIONAL CONSTRAINTS (END OF RFP) ---\n{tail_text}")
                
            focused_rfp_content = "\n\n".join(combined_parts)
            logger.info(f"✅ Extracted focused content: {len(focused_rfp_content)} chars (reduced from {len(rfp_text)} chars)")

    rfp_text = focused_rfp_content

    # ---------- Retrieve KB context ----------
    fallback_fields = [
        getattr(project, "name", None),
        getattr(project, "domain", None),
        getattr(project, "complexity", None),
        getattr(project, "tech_stack", None),
        getattr(project, "use_cases", None),
        getattr(project, "compliance", None),
        str(getattr(project, "duration", "")) if getattr(project, "duration", None) else None,
    ]
    fallback_text = " ".join(f for f in fallback_fields if f and str(f).strip())

    # If completely empty, create a detailed specific prompt instead of returning empty scope
    if not (rfp_text.strip() or fallback_text.strip()):
        logger.warning(f"⚠️ No RFP text or project metadata for project {project.id}. Using detailed generic prompt.")
        fallback_text = """
Project Requirements:
- Project Type: Software Development Project
- Domain: Web Application Development
- Complexity: Medium
- Tech Stack: React, Node.js, PostgreSQL, AWS
- Duration: 6 months
- Team Size: 5-7 people

Project Scope:
Create a comprehensive project plan with the following phases:

1. Requirements & Planning Phase (1 month)
   - Gather and document requirements
   - Create technical specifications
   - Set up project infrastructure
   Owner: Project Manager
   Resources: Business Analyst, Technical Lead

2. Design Phase (1 month)
   - Design system architecture
   - Create UI/UX mockups
   - Database schema design
   Owner: Solution Architect
   Resources: UI/UX Designer, Database Administrator

3. Development Phase (2.5 months)
   - Frontend development (React)
   - Backend API development (Node.js)
   - Database implementation
   - Integration testing
   Owner: Technical Lead
   Resources: Frontend Developer, Backend Developer, QA Engineer

4. Testing & QA Phase (1 month)
   - Unit testing
   - Integration testing
   - User acceptance testing
   - Bug fixes
   Owner: QA Lead
   Resources: QA Engineer, Backend Developer

5. Deployment & Go-Live (0.5 months)
   - Production deployment
   - Performance optimization
   - Documentation
   - Training
   Owner: DevOps Engineer
   Resources: Technical Lead, Backend Developer

Generate activities with realistic start/end dates, proper role assignments, and meaningful descriptions.
"""

    kb_results = _rag_retrieve(rfp_text or fallback_text)
    kb_chunks = []
    stop = False
    for group in kb_results:
        for ch in group["chunks"]:
            chunk_tokens = len(tokenizer.encode(ch["content"]))
            if used_tokens + chunk_tokens > max_total_tokens:
                stop = True
                break
            kb_chunks.append(ch["content"])
            used_tokens += chunk_tokens
        if stop:
            break

    # Recalculate rfp_tokens length for logging since we overwrote the variable
    rfp_tokens_count = len(tokenizer.encode(rfp_text or ""))
    logger.info(
        f"Final RFP tokens: {rfp_tokens_count}, KB tokens: {used_tokens - rfp_tokens_count}, Total: {used_tokens}/{max_total_tokens}"
    )

    # ---------- Load questions.json (if exists) and build Q&A context ----------
    questions_context = None
    try:
        q_blob_name = f"{PROJECTS_BASE}/{project.id}/questions.json"
        if await azure_blob.blob_exists(q_blob_name):
            q_bytes = await azure_blob.download_bytes(q_blob_name)
            q_json = json.loads(q_bytes.decode("utf-8"))

            q_lines = []
            for category in q_json.get("questions", []):
                cat_name = category.get("category", "General")
                q_lines.append(f"### {cat_name}")
                for item in category.get("items", []):
                    q = item.get("question", "").strip()
                    a = item.get("user_understanding", "").strip() or "(unanswered)"
                    comment = item.get("comment", "").strip()
                    line = f"Q: {q}\nA: {a}"
                    if comment:
                        line += f"\nComment: {comment}"
                    q_lines.append(line)

            questions_context = "\n".join(q_lines)
            logger.info(f"Loaded {len(q_lines)} question lines for project {project.id}")
        else:
            logger.info(f"No questions.json found for project {project.id}, skipping Q&A context.")

    except Exception as e:
        logger.warning(f" Could not include questions.json context: {e}")
        questions_context = None

    # ---------- Fetch company rate card roles ----------
    rate_card_roles = []
    try:
        rate_map = await get_rate_map_for_project(db, project)
        rate_card_roles = list(rate_map.keys())
        logger.info(f"📋 Fetched {len(rate_card_roles)} roles from company rate card: {', '.join(rate_card_roles[:10])}")
    except Exception as e:
        logger.warning(f"⚠️ Could not fetch rate card roles: {e}")
        rate_card_roles = list(ROLE_RATE_MAP.keys())

    # ---------- Load closeout actuals from DB (if project was previously closed) ----------
    closeout_actuals_context = None
    is_closed = False
    resource_actuals = []
    try:
        project_status = getattr(project, "status", None) or "draft"
        project_closed_at = getattr(project, "closed_at", None)
        is_closed = (project_status == "closed") or (project_closed_at is not None)
        logger.info(f"Project {project.id} status={project_status}, closed_at={project_closed_at}, is_closed={is_closed}")

        if is_closed:
            from app.models import ResourceActual
            ra_result = await db.execute(
                select(ResourceActual).where(ResourceActual.project_id == project.id)
            )
            ra_orm_objects = ra_result.scalars().all()
            logger.info(f"Found {len(ra_orm_objects)} resource actuals for project {project.id}")

            # Convert ORM objects to plain dicts immediately to avoid session expiry issues
            for ra_orm in ra_orm_objects:
                ra_dict = type('ResourceActualData', (), {
                    'resource_name': ra_orm.resource_name,
                    'rate_per_month': ra_orm.rate_per_month,
                    'estimated_effort_months': ra_orm.estimated_effort_months,
                    'actual_effort_months': ra_orm.actual_effort_months,
                    'estimated_cost': ra_orm.estimated_cost,
                    'actual_cost': ra_orm.actual_cost,
                    'notes': ra_orm.notes,
                })()
                resource_actuals.append(ra_dict)
                logger.info(f"🔴 Loaded actual: {ra_dict.resource_name} -> actual_effort={ra_dict.actual_effort_months}")

            if resource_actuals:
                actuals_lines = [
                    "ACTUAL PERFORMANCE DATA FROM PREVIOUS CLOSEOUT:",
                    "This project was previously executed and closed out with real measurements.",
                    "You MUST use these ACTUAL effort values when generating the resourcing plan.",
                    ""
                ]
                for ra in resource_actuals:
                    variance = ((ra.actual_effort_months - ra.estimated_effort_months) / ra.estimated_effort_months * 100) if ra.estimated_effort_months > 0 else 0
                    actuals_lines.append(f"Resource: {ra.resource_name}")
                    actuals_lines.append(f"  Rate: ${ra.rate_per_month:,.0f}/month")
                    actuals_lines.append(f"  Estimated Effort: {ra.estimated_effort_months} months")
                    actuals_lines.append(f"  ACTUAL Effort: {ra.actual_effort_months} months ({variance:+.1f}% variance) - USE THIS VALUE")
                    actuals_lines.append(f"  Estimated Cost: ${ra.estimated_cost:,.0f}")
                    actuals_lines.append(f"  ACTUAL Cost: ${ra.actual_cost:,.0f}")
                    if ra.notes:
                        actuals_lines.append(f"  Notes: {ra.notes}")
                    actuals_lines.append("")

                actuals_lines.append("INSTRUCTION: When generating the resourcing plan, use the ACTUAL effort months for each resource listed above.")
                actuals_lines.append("For activities involving these resources, set Effort Months based on the actual effort data.")
                closeout_actuals_context = "\n".join(actuals_lines)
                logger.info(f"Loaded {len(resource_actuals)} resource actuals for project {project.id}")
    except Exception as e:
        logger.warning(f"Could not load closeout actuals: {e}")

    # ---------- Build + query with AI AGENT ----------
    try:
        # Import agent service
        from app.services.agent_service import get_scoping_agent

        logger.info(f"🤖 Using AI Agent for intelligent scope generation...")

        # Get the agent
        agent = get_scoping_agent()

        # Prepare project information for agent
        project_name = getattr(project, "name", "Untitled Project")
        domain = getattr(project, "domain", "") or "General"
        tech_stack = getattr(project, "tech_stack", "") or "Not specified"
        complexity = getattr(project, "complexity", None)
        use_cases = getattr(project, "use_cases", None)
        company_id = str(getattr(project, "company_id", ""))

        # Use RFP text or fallback
        final_rfp_text = rfp_text or fallback_text

        # Snapshot raw user-provided values BEFORE the agent fills them in.
        # Used later to detect which fields the AI inferred vs. the user provided.
        original_tech_stack = getattr(project, "tech_stack", None) or ""
        original_domain = getattr(project, "domain", None) or ""
        original_complexity = getattr(project, "complexity", None) or ""
        original_use_cases = getattr(project, "use_cases", None) or ""
        original_compliance = getattr(project, "compliance", None) or ""
        original_duration = str(getattr(project, "duration", None) or "").strip()


        # Call agent to generate scope
        logger.info(f"🚀 Agent starting autonomous reasoning for project: {project_name}")
        duration = str(getattr(project, "duration", "") or "").strip()

        # Fetch Past Proposals and format them
        logger.info(f"🔎 Retrieving Past SOW Proposals for calibration...")
        past_proposals = _retrieve_past_proposals(final_rfp_text, k=3)
        past_proposals_context = None
        if past_proposals:
            pp_lines = []
            for pp in past_proposals:
                pp_lines.append(f"""
- **Past Client**: {pp.get('client_name')}
- **Domain**: {pp.get('domain')}
- **Duration**: {pp.get('duration_months')} months
- **Team Size**: {pp.get('team_size')}
- **Total Cost**: ${pp.get('total_cost'):,.0f}
- **Summary**: {pp.get('summary')}
""")
            past_proposals_context = "\n".join(pp_lines)
            logger.info(f"✅ Found {len(past_proposals)} similar past proposals for calibration")

        agent_scope = await agent.generate_scope(
            project_name=project_name,
            domain=domain,
            tech_stack=tech_stack,
            rfp_text=final_rfp_text,
            company_id=company_id,
            db_session=db,
            complexity=complexity,
            use_cases=use_cases,
            duration=duration,
            closeout_actuals_context=closeout_actuals_context,
            past_proposals_context=past_proposals_context
        )
        
        logger.info(f"✅ Agent completed scope generation")
        
        # Transform agent output to match expected format
        # Agent returns structured data, we need to convert to activities format
        raw = _transform_agent_output_to_scope_format(agent_scope, project)
        
        # Log what was generated
        logger.info(f"📊 Agent generated scope with:")
        logger.info(f"   - Team roles: {len(agent_scope.get('team_composition', []))}")
        logger.info(f"   - Activities: {len(raw.get('activities', []))}")
        logger.info(f"   - Total cost: ${agent_scope.get('cost_summary', {}).get('total_cost', 0):,.2f}")
        logger.info(f"   - Reasoning steps: {agent_scope.get('_agent_metadata', {}).get('reasoning_steps', 0)}")
        
        # Clean and format the scope
        cleaned_scope = await clean_scope(db, raw, project=project)

        # Post-process: Override resourcing plan with closeout actuals
        logger.info(f"🔴 POST-PROCESS CHECK: is_closed={is_closed}, resource_actuals count={len(resource_actuals)}")
        if is_closed and resource_actuals:
            logger.info(f"🔴 APPLYING closeout actuals override to resourcing plan")
            try:
                cleaned_scope = _apply_closeout_actuals_to_scope(cleaned_scope, resource_actuals)
                logger.info(f"🔴 Successfully applied closeout actuals override")
            except Exception as e:
                logger.error(f"🔴 EXCEPTION in _apply_closeout_actuals_to_scope: {e}", exc_info=True)
        else:
            logger.warning(f"🔴 SKIPPED closeout override: is_closed={is_closed}, resource_actuals={len(resource_actuals)}")

        # Update project fields from generated overview
        overview = cleaned_scope.get("overview", {})
        if overview:
            project.name = overview.get("Project Name") or project.name
            project.domain = overview.get("Domain") or project.domain
            project.complexity = overview.get("Complexity") or project.complexity
            project.tech_stack = overview.get("Tech Stack") or project.tech_stack
            project.use_cases = overview.get("Use Cases") or project.use_cases
            project.compliance = overview.get("Compliance") or project.compliance
            project.duration = str(overview.get("Duration") or project.duration)

            try:
                await db.commit()
                await db.refresh(project)
                logger.info(f"✅ Project metadata updated from agent-generated scope for project {project.id}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to update project metadata: {e}")

        # Step 1.4: Compute inferred fields (AI filled in what user left blank)
        try:
            original_values = {
                "Tech Stack": original_tech_stack,
                "Domain": original_domain,
                "Complexity": original_complexity,
                "Use Cases": original_use_cases,
                "Compliance": original_compliance,
                "Duration": original_duration,
            }
            overview_ai = cleaned_scope.get("overview", {})
            inferred = []
            for field_key, orig_val in original_values.items():
                ai_val = overview_ai.get(field_key)
                # Flag as inferred if: user had nothing AND AI put something
                if not orig_val and ai_val and str(ai_val).strip():
                    inferred.append(field_key)
            cleaned_scope["inferred_fields"] = inferred
            if inferred:
                logger.info(f"🔍 Inferred fields (AI filled in): {inferred}")
            else:
                logger.info("✅ No inferred fields — all overview values were user-provided.")
        except Exception as e:
            logger.warning(f"Failed to compute inferred fields: {e}")
            cleaned_scope["inferred_fields"] = []

        # Step 1.5: Validate against industry benchmarks
        from app.utils.confidence import calculate_confidence
        warnings = []
        try:
            from app.utils.benchmarks import validate_against_benchmark
            warnings = validate_against_benchmark(
                cleaned_scope,
                domain=getattr(project, "domain", ""),
                complexity=getattr(project, "complexity", "")
            )
            if warnings:
                cleaned_scope["_warnings"] = warnings
                logger.info(f"⚠️ Added {len(warnings)} benchmark warnings to scope.")
        except Exception as e:
            logger.warning(f"Benchmark validation failed: {e}")
            
        # Step 1.6: Calculate Confidence Score
        try:
            confidence_data = calculate_confidence(
                past_proposals_found=len(past_proposals) if past_proposals_context else 0,
                benchmark_warnings=warnings,
                is_closed_override=is_closed and bool(resource_actuals)
            )
            cleaned_scope["confidence_score"] = confidence_data["score"]
            cleaned_scope["confidence_reasons"] = confidence_data["reasons"]
            logger.info(f"🎯 Assigned confidence score: {confidence_data['score']}")
        except Exception as e:
            logger.warning(f"Failed to calculate confidence score: {e}")


        # Step 2: Generate + store architecture diagram
        try:
            blob_base_path = f"{PROJECTS_BASE}/{getattr(project, 'id', 'unknown')}"
            _, arch_dict = await generate_architecture(
                db, project, rfp_text, kb_chunks, blob_base_path
            )
            cleaned_scope["architecture_diagram"] = arch_dict or None
        except Exception as e:
            logger.warning(f"Architecture diagram generation failed: {e}")
            cleaned_scope["architecture_diagram"] = None

        # Step 3: Auto-save finalized_scope.json in Azure Blob + DB
        try:

            result = await db.execute(
                select(models.ProjectFile).filter(
                    models.ProjectFile.project_id == project.id,
                    models.ProjectFile.file_name == "finalized_scope.json",
                )
            )
            old_file = result.scalars().first()
            if old_file:
                logger.info(f"Overwriting existing finalized_scope.json for project {project.id}")
            else:
                old_file = models.ProjectFile(
                    project_id=project.id,
                    file_name="finalized_scope.json",
                )

            blob_name = f"{PROJECTS_BASE}/{project.id}/finalized_scope.json"

            await azure_blob.upload_bytes(
                json.dumps(cleaned_scope, ensure_ascii=False, indent=2).encode("utf-8"),
                blob_name,
                overwrite=True, 
            )

            old_file.file_path = blob_name
            db.add(old_file)
            await db.commit()
            await db.refresh(old_file)

            logger.info(f"✅ finalized_scope.json saved for project {project.id}")

        except Exception as e:
            logger.warning(f"⚠️  Failed to auto-save finalized_scope.json: {e}")
        
        return cleaned_scope

    except Exception as e:
        logger.error(f"❌ Agent scope generation failed: {e}", exc_info=True)
        return {}



async def regenerate_from_instructions(
    db: AsyncSession,
    project: models.Project,
    draft: dict,
    instructions: str
) -> dict:
    """
    Regenerate the project scope from user instructions using a creative AI-guided prompt.
    Enhances activity sequencing, roles, and effort estimates while preserving valid JSON structure.
    """
    logger.info(f" Regenerating scope for project {project.id} with creative AI response...")

    if not instructions or not instructions.strip():
        cleaned = await clean_scope(db, draft, project=project)
        # Apply closeout actuals even without instructions
        try:
            project_status = getattr(project, "status", None) or "draft"
            project_closed_at = getattr(project, "closed_at", None)
            is_closed = (project_status == "closed") or (project_closed_at is not None)
            if is_closed:
                from app.models import ResourceActual
                ra_result = await db.execute(
                    select(ResourceActual).where(ResourceActual.project_id == project.id)
                )
                resource_actuals = ra_result.scalars().all()
                if resource_actuals:
                    cleaned = _apply_closeout_actuals_to_scope(cleaned, resource_actuals)
                    logger.info(f"🔴 [regenerate-no-instructions] Applied closeout actuals override")
        except Exception as e:
            logger.warning(f"Could not apply closeout actuals: {e}")
        return {**cleaned, "_finalized": True}



    prompt = f"""
You are an **expert AI project planner and delivery architect** responsible for maintaining a project scope in JSON format.

You are given:
1. The current draft project scope (JSON with keys: `overview`, `activities`, `resourcing_plan`).
2. The user’s latest change instructions.

Your task:
- **Understand** the user’s intent (instructions may be in natural language).
- **Regenerate** the scope accordingly:
  - Apply all user instructions faithfully.
  - Preserve structure and realism of the plan.
  - Re-calculate activity dates, dependencies, and efforts using the rules below.
  - Reflect improvements like “optimize”, “simplify”, “rebalance”, or “add QA phase”.
  - Apply all user instructions faithfully.
  - Preserve structure and realism of the plan.
  - Re-calculate activity dates, dependencies, and efforts using the rules below.
  - Reflect improvements like “optimize”, “simplify”, “rebalance”, or “add QA phase”.

---

### RULES OF MODIFICATION

####  Schema
- Preserve the same top-level keys: `overview`, `activities`, `resourcing_plan`.
- Every activity must have: "ID", "Activities", "Owner", "Resources",
- "Start Date", "End Date", "Effort Months"
- Use valid ISO dates (`yyyy-mm-dd`).
- Keep total duration ≤ 12 months.

**CRITICAL: What activities look like**
CORRECT activity example:
```json
{{
  "ID": 1,
  "Activities": "Project Initiation and Requirements Gathering",
  "Owner": "Project Manager",
  "Resources": "Business Analyst, Data Architect",
  "Start Date": "2025-01-15",
  "End Date": "2025-02-28",
  "Effort Months": 1.5
}}
```

WRONG activity example (DO NOT DO THIS):
```json
{{
  "ID": 1,
  "Activities": "Project Manager",  (WRONG: This is a role name, not an activity)\n
  "Owner": "Unassigned",  (WRONG: Must have a real owner)\n
  "Resources": "",\n
  "Start Date": "2025-01-15",
  "End Date": "2025-02-15",
  "Effort Months": 1
}}
```

####  Temporal Adjustment Rules
Use these to keep the schedule consistent and continuous.

**Add new activity**  
1. Identify the logical chronological position to insert the new activity based on its technical phase.
2. Calculate its `Start Date` and `End Date`.
3. CRITICAL MATHEMATICAL STEP: You MUST shift the `Start Date` and `End Date` of EVERY SINGLE activity that follows the new activity LATER in time by exactly the duration of the new activity. Do not let the new activity overlap with subsequent activities. If you fail to shift the following dates, the timeline will be broken.

**Delete activity**  
- Remove it completely.  
- Shift all subsequent activities EARLIER in time to close the gap and maintain a continuous timeline.

**Split activity into two**  
- Divide one activity into two consecutive ones.  
- Combined effort_days = original.  
- Combined duration = original.  
- Other activities’ dates shift if the total duration changes.

**Merge two activities**
- Combine both into one.
- start_date = min(start of both)
- end_date = max(end of both)
- effort_days = sum(efforts of both)

**Duration Update**
- If you add or remove activities, you MUST update the `overview.Duration` field to correctly reflect the new overall timeline (from first start date to last end date).

####  Role Management Rules
Critical: When user requests to add or remove roles, you MUST update BOTH activities and resourcing_plan.

**IMPORTANT: All changes are INCREMENTAL - preserve existing activities unless explicitly deleted!**

**Remove a role (e.g., "remove Business Analyst")**:
1. Keep ALL existing activities
2. Find all activities where the role is the Owner
3. Reassign those activities to another appropriate role
4. Remove the role from ALL Resources fields across all activities
5. DO NOT delete any activities - only change role assignments
6. Example: If removing "Business Analyst":
   - Activity: "Owner": "Business Analyst" -> change to "Owner": "Product Manager"\n
   - Activity: "Resources": "Business Analyst, Data Engineer" -> change to "Resources": "Data Engineer"\n
   - Keep ALL other activities unchanged
   - resourcing_plan: will be auto-calculated

**Add more of an existing role (e.g., "add 1 more Backend Developer")**:
1. **CRITICAL**: Keep ALL existing activities and roles
2. "Add 1 more" means INCREASE allocation, not replace
3. To increase Backend Developer allocation:
   - Add "Backend Developer" to Resources field of MORE existing activities
   - OR extend date ranges of activities that already have Backend Developer
   - OR create 1-2 NEW activities specifically for Backend Developer
4. **DO NOT remove any existing activities or roles**
5. Example: If you have 10 activities and "add 1 Backend Developer":
   - Original: 10 activities with Backend Developer in 3 of them
   - After: Same 10 activities PLUS Backend Developer added to 2-3 more activities
   - Result: Backend Developer effort increases from 3 months to 5-6 months

**Add a new role type (e.g., "add Security Engineer")**:
1. **CRITICAL**: Keep ALL existing activities and roles
2. Add new activities for this role OR add to Resources field of existing activities
3. DO NOT remove any existing activities
4. The resourcing_plan will be auto-generated based on activities

####  Discount Rules
When user requests a discount (e.g., "apply 5% discount", "give 10% discount"):
1. **DO NOT change activities, dates, or efforts**
2. **ONLY note the discount percentage in a special field**
3. Add a new field: "discount_percentage": <number> (e.g., 5 for 5%, 10 for 10%)
4. The discount will be applied automatically during cost calculation
5. Keep all activities, roles, and resourcing_plan calculations unchanged

### Scheduling Rules
- Activities should follow **semi-parallel execution** — overlap realistically but maintain logical order.
- If two activities are **independent**, overlap their timelines by **70–80%** of their duration (not full overlap).
- If one activity **depends** on another, allow a small overlap of **10-15%** near the end of the predecessor if feasible.
- Avoid full serialization unless strictly required by dependency.
- Avoid full parallelism where all tasks start together — stagger independent ones by **10-15%**.
- Ensure overall project duration stays **≤ 12 months**.
- The first activity must always start today.
---

### Regeneration Logic
- Clean and re-order activities logically.
- Maintain coherent dependencies and sequential flow.
- Adjust `overview.duration_months` automatically based on new total project span.
- Keep resource roles realistic and consistent with activities (Backend Developer, Data Engineer, QA Analyst, etc.).
- Reflect optimization or simplification requests (e.g., reduce redundant steps, consolidate phases).

---

###  Output Rules
- Output **only valid JSON** — no markdown, no explanations, no reasoning.
- Must include:
  - `overview` → Project metadata (name, domain, complexity, tech stack, etc.)
  - `activities` → COMPLETE updated list with ALL modifications applied
  - `resourcing_plan` → OPTIONAL (will be auto-calculated from activities)
  - `discount_percentage` → OPTIONAL (only if user requested discount, e.g., 5 for 5%, 10 for 10%)
- **CRITICAL**: If user says "remove [role]", that role MUST NOT appear in ANY activity's Owner or Resources field
- **CRITICAL**: If user says "add 1 more [role]", ADD to existing activities, DO NOT replace them
- **CRITICAL**: If user says "apply X% discount", include "discount_percentage": X in output
- **Dont change schema or field names.**
- **PRESERVE all activities** - only modify/add/remove specific items mentioned by user

---

User Instructions:
{instructions}

Current Draft Scope:
{json.dumps(draft, indent=2, ensure_ascii=False)}

Return only the updated JSON.
"""


    # ================================================================
    # PRE-PROCESSING: Apply activity name removal DIRECTLY to draft
    # before Ollama call — guarantees it works even if Ollama fails
    # ================================================================
    import re as _re
    if instructions and any(word in instructions.lower() for word in ['remove', 'delete']):
        instr_lower = instructions.lower()
        removal_phrases = _re.findall(
            r'(?:remove|delete)\s+([^\n,\.]+)',
            instr_lower,
            _re.IGNORECASE
        )
        common_roles_lower = [
            'project manager', 'business analyst', 'data architect', 'data engineer',
            'backend developer', 'frontend developer', 'qa engineer', 'devops engineer',
            'cloud architect', 'data analyst', 'ux designer', 'ai/ml engineer',
            'sustainability analyst', 'scrum master'
        ]
        for phrase in removal_phrases:
            phrase_cleaned = phrase.strip().lower()
            # Skip pure role-removal instructions (handled separately)
            if any(role in phrase_cleaned for role in common_roles_lower):
                continue
            original_count = len(draft.get('activities', []))
            meaningful_words = [w for w in phrase_cleaned.split() if len(w) > 3]
            draft['activities'] = [
                act for act in draft.get('activities', [])
                if phrase_cleaned not in act.get('Activities', '').lower()
                and not (meaningful_words and any(all(w in act.get('Activities', '').lower() for w in meaningful_words) for _ in [1]))
            ]
            removed = original_count - len(draft.get('activities', []))
            if removed > 0:
                # Re-number IDs
                for i, act in enumerate(draft['activities'], start=1):
                    act['ID'] = i
                logger.info(f"✅ PRE-PROCESSING: Removed {removed} activities matching '{phrase_cleaned}'")
            else:
                logger.info(f"ℹ️ PRE-PROCESSING: No activities matched '{phrase_cleaned}'")

    # ---- Query Azure OpenAI for reliable instruction-following ----
    try:
        from app.config.config import AZURE_OPENAI_DEPLOYMENT
        azure_client = get_async_azure_client()
        response = await azure_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert project scope editor. You must return only valid JSON — no markdown, no explanation, no code fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        raw_text = response.choices[0].message.content
        logger.info(f"🤖 Azure OpenAI regen response length: {len(raw_text)} chars")
        logger.debug(f"Azure regen response (first 500 chars): {raw_text[:500]}")
        updated_scope = _extract_json(raw_text)

        logger.info(f"📊 Extracted scope structure: overview={bool(updated_scope.get('overview'))}, "
                   f"activities={len(updated_scope.get('activities', []))}, "
                   f"resourcing_plan={len(updated_scope.get('resourcing_plan', []))}")

        # Validate activity count - prevent accidental scope replacement
        original_activity_count = len(draft.get('activities', []))
        new_activity_count = len(updated_scope.get('activities', []))
        is_removal_instruction = any(word in instructions.lower() for word in ['remove', 'delete'])

        # Advanced validation: Check if activities are valid/meaningful
        activities_are_valid = True
        validation_failures = []

        if updated_scope.get('activities'):
            unassigned_count = sum(1 for act in updated_scope['activities'] if act.get('Owner', '').lower() in ['unassigned', ''])


            # Check if activity names are just role names (common LLM mistake)
            common_roles = ['project manager', 'business analyst', 'data architect', 'data engineer',
                           'backend developer', 'frontend developer', 'qa engineer', 'devops engineer',
                           'cloud architect', 'data analyst', 'ux designer']
            role_name_activities = sum(1 for act in updated_scope['activities']
                                      if act.get('Activities', '').lower().strip() in common_roles)

            # Check if all activities have identical dates (suspicious)
            dates = [(act.get('Start Date'), act.get('End Date')) for act in updated_scope['activities']]
            unique_date_pairs = len(set(dates))

            # Validation thresholds
            if unassigned_count > new_activity_count * 0.5:  # More than 50% unassigned
                activities_are_valid = False
                validation_failures.append(f"{unassigned_count}/{new_activity_count} activities have Unassigned owner")

            if role_name_activities > new_activity_count * 0.3:  # More than 30% are just role names
                activities_are_valid = False
                validation_failures.append(f"{role_name_activities}/{new_activity_count} activities are named after roles (e.g. 'Project Manager', 'Data Engineer')")

            if unique_date_pairs == 1 and new_activity_count > 1:  # All activities have same dates
                activities_are_valid = False
                validation_failures.append(f"All {new_activity_count} activities have identical dates: {dates[0]}")

        # If LLM significantly reduced activities OR created invalid activities, restore original
        if (new_activity_count < (original_activity_count * 0.7) and not is_removal_instruction) or not activities_are_valid:
            if not activities_are_valid:
                logger.error(f"❌ LLM GENERATED INVALID ACTIVITIES!")
                for failure in validation_failures:
                    logger.error(f"   - {failure}")
            else:
                logger.error(f"❌ LLM LOST TOO MANY ACTIVITIES! Original: {original_activity_count}, New: {new_activity_count}")

            logger.error(f"   User instruction: '{instructions[:100]}'")
            logger.error(f"   🔧 Auto-restoring original activities to prevent data loss")

            # Restore original activities
            updated_scope["activities"] = draft.get("activities", [])
            if "resourcing_plan" not in updated_scope or not updated_scope.get("resourcing_plan"):
                updated_scope["resourcing_plan"] = draft.get("resourcing_plan", [])

            logger.info(f"   ✅ Restored {len(updated_scope['activities'])} valid activities from draft")

        # Log roles found in activities
        if updated_scope.get('activities'):
            owners = set(act.get('Owner', 'Unknown') for act in updated_scope['activities'])
            all_resources = set()
            for act in updated_scope['activities']:
                resources = act.get('Resources', '')
                if resources:
                    all_resources.update(r.strip() for r in str(resources).split(',') if r.strip())
            all_roles = owners | all_resources
            logger.info(f"🎭 Roles in LLM response - Owners: {owners}, Resources: {all_resources}")

            # Validate that "remove" instructions were followed
            if instructions and 'remove' in instructions.lower():
                for role in all_roles:
                    if role.lower() in instructions.lower() and 'remove' in instructions.lower():
                        logger.error(f"❌ LLM FAILED to remove '{role}' - still present in activities despite user instruction!")

            # Validate that "add" instructions were followed
            if instructions and 'add' in instructions.lower():
                # This is harder to validate automatically, but we log for manual inspection
                logger.info(f"ℹ️ User requested to add role(s). Current roles: {all_roles}")

        # Post-processing fallback: manually remove roles if LLM failed
        if instructions and 'remove' in instructions.lower() and updated_scope.get('activities'):
            # Extract role to remove from instructions (basic pattern matching)
            import re
            # Pattern to match "remove <role>" where role can be multi-word
            # Matches everything after "remove" until end of string or common delimiters
            remove_pattern = r'remove\s+([a-zA-Z\s]+?)(?:\s*(?:from|,|\.|\band\b|$))'
            match = re.search(remove_pattern, instructions.lower(), re.IGNORECASE)
            if match:
                role_to_remove = match.group(1).strip()
                logger.info(f"🔧 Post-processing: attempting to remove '{role_to_remove}'")

                # Track if we made changes
                changes_made = False

                # Process each activity
                for act in updated_scope['activities']:
                    # Check if this role is the owner
                    if act.get('Owner', '').lower() == role_to_remove or role_to_remove in act.get('Owner', '').lower():
                        # Find a replacement owner from resources or use a default
                        resources = act.get('Resources', '')
                        if resources and resources.strip():
                            # Use the first resource as the new owner
                            new_owner = resources.split(',')[0].strip()
                            # Remove new owner from resources to avoid duplication
                            remaining_resources = [r.strip() for r in resources.split(',')[1:] if r.strip()]
                            act['Owner'] = new_owner
                            act['Resources'] = ', '.join(remaining_resources)
                            logger.info(f"  → Reassigned activity '{act.get('Activities', 'Unknown')}' from removed role to '{new_owner}'")
                            changes_made = True
                        else:
                            # No resources available, use a generic default
                            act['Owner'] = 'Project Manager'
                            logger.info(f"  → Reassigned activity '{act.get('Activities', 'Unknown')}' from removed role to 'Project Manager'")
                            changes_made = True

                    # Remove from resources field
                    if act.get('Resources'):
                        resources_list = [r.strip() for r in str(act['Resources']).split(',') if r.strip()]
                        # Filter out the role to remove (case-insensitive partial match)
                        filtered_resources = [r for r in resources_list
                                             if role_to_remove not in r.lower() and r.lower() != role_to_remove]
                        if len(filtered_resources) != len(resources_list):
                            act['Resources'] = ', '.join(filtered_resources)
                            changes_made = True

                if changes_made:
                    logger.info(f"✅ Post-processing successfully removed role '{role_to_remove}' from activities")

        # ---- Post-processing: Activity name-based removal ----
        # Directly remove activities by name when user says "remove <activity name>"
        if instructions and any(word in instructions.lower() for word in ['remove', 'delete']) and updated_scope.get('activities'):
            import re
            instr_lower = instructions.lower()

            # Extract everything after "remove" or "delete" keyword
            removal_phrases = re.findall(
                r'(?:remove|delete)\s+([^\n,\.]+)',
                instr_lower,
                re.IGNORECASE
            )

            for phrase in removal_phrases:
                phrase_cleaned = phrase.strip().lower()
                # Skip if it looks like a role name instruction (already handled above)
                common_roles = ['project manager', 'business analyst', 'data architect', 'data engineer',
                               'backend developer', 'frontend developer', 'qa engineer', 'devops engineer',
                               'cloud architect', 'data analyst', 'ux designer', 'ai/ml engineer',
                               'sustainability analyst', 'scrum master']
                if any(role in phrase_cleaned for role in common_roles):
                    continue

                original_count = len(updated_scope['activities'])
                # Remove activities whose name contains the phrase (substring match)
                updated_scope['activities'] = [
                    act for act in updated_scope['activities']
                    if phrase_cleaned not in act.get('Activities', '').lower()
                    and not any(all(w in act.get('Activities', '').lower() for w in phrase_cleaned.split() if len(w) > 3) for _ in [1])
                ]
                removed_count = original_count - len(updated_scope['activities'])
                if removed_count > 0:
                    logger.info(f"✅ Post-processing: removed {removed_count} activities matching '{phrase_cleaned}'")

                    # Re-number remaining activities sequentially
                    for i, act in enumerate(updated_scope['activities'], start=1):
                        act['ID'] = i
                else:
                    logger.info(f"ℹ️ Post-processing: no activities matched removal phrase '{phrase_cleaned}'")

        # Post-processing: parse discount percentage from instructions
        if instructions:
            import re
            # Pattern to match discount requests: "5% discount", "apply 10% discount", "give 15% discount", etc.
            discount_patterns = [
                r'(\d+)\s*%\s*discount',
                r'discount\s+(?:of\s+)?(\d+)\s*%',
                r'apply\s+(\d+)\s*%',
                r'give\s+(\d+)\s*%',
            ]
            discount_found = False
            for pattern in discount_patterns:
                match = re.search(pattern, instructions.lower())
                if match:
                    discount_percentage = int(match.group(1))
                    logger.info(f"💰 Post-processing: detected {discount_percentage}% discount request")

                    # Add discount to updated_scope if not already present
                    if "discount_percentage" not in updated_scope or not updated_scope.get("discount_percentage"):
                        updated_scope["discount_percentage"] = discount_percentage
                        logger.info(f"  → Added discount_percentage: {discount_percentage}")
                    discount_found = True
                    break

            if not discount_found and any(word in instructions.lower() for word in ['discount', 'reduction', 'reduce cost']):
                logger.warning(f"⚠️ User mentioned discount but couldn't parse percentage. Instructions: {instructions[:100]}")

        # Safety check: if LLM returned empty activities, preserve original
        if not updated_scope.get("activities") or len(updated_scope.get("activities", [])) == 0:
            logger.warning(f"⚠️ LLM returned empty activities - preserving original draft activities")
            logger.info(f"📋 Original draft had {len(draft.get('activities', []))} activities")
            # Preserve original activities and resourcing_plan, but update overview if changed
            updated_scope["activities"] = draft.get("activities", [])
            if "resourcing_plan" not in updated_scope or not updated_scope.get("resourcing_plan"):
                updated_scope["resourcing_plan"] = draft.get("resourcing_plan", [])

        # Force strictly recalculating the final duration based on the new activities
        updated_scope["_force_duration_recalc"] = True
        
        cleaned = await clean_scope(db, updated_scope, project=project)
        # Remove the internal flag after clean_scope handles it
        if "_force_duration_recalc" in cleaned:
            del cleaned["_force_duration_recalc"]
            
        logger.info(f"✅ Cleaned scope: {len(cleaned.get('activities', []))} activities, "
                   f"{len(cleaned.get('resourcing_plan', []))} resources, "
                   f"Duration: {cleaned.get('overview', {}).get('Duration', 'N/A')}")

    except Exception as e:
        logger.error(f" Creative regeneration failed: {e}")
        cleaned = await clean_scope(db, draft, project=project)

    # ---- Apply closeout actuals override (same as generate_project_scope) ----
    try:
        project_status = getattr(project, "status", None) or "draft"
        project_closed_at = getattr(project, "closed_at", None)
        is_closed = (project_status == "closed") or (project_closed_at is not None)
        logger.info(f"🔴 [regenerate] Project {project.id} status={project_status}, is_closed={is_closed}")

        if is_closed:
            from app.models import ResourceActual
            ra_result = await db.execute(
                select(ResourceActual).where(ResourceActual.project_id == project.id)
            )
            resource_actuals = ra_result.scalars().all()
            logger.info(f"🔴 [regenerate] Found {len(resource_actuals)} resource actuals")

            if resource_actuals:
                cleaned = _apply_closeout_actuals_to_scope(cleaned, resource_actuals)
                logger.info(f"🔴 [regenerate] Applied closeout actuals override")
    except Exception as e:
        logger.warning(f"🔴 [regenerate] Could not apply closeout actuals: {e}")

    # ---- Update project metadata from overview ----
    overview = cleaned.get("overview", {})
    if overview:
        project.name = overview.get("Project Name") or project.name
        project.domain = overview.get("Domain") or project.domain
        project.complexity = overview.get("Complexity") or project.complexity
        project.tech_stack = overview.get("Tech Stack") or project.tech_stack
        project.use_cases = overview.get("Use Cases") or project.use_cases
        project.compliance = overview.get("Compliance") or project.compliance
        project.duration = str(overview.get("Duration") or project.duration)
        await db.commit()
        await db.refresh(project)
        logger.info(f" Project metadata synced for project {project.id}")

    # ---- Overwrite finalized_scope.json in Blob ----
    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project.id,
            models.ProjectFile.file_name == "finalized_scope.json",
        )
    )
    old_file = result.scalars().first() or models.ProjectFile(
        project_id=project.id, file_name="finalized_scope.json"
    )

    blob_name = f"{PROJECTS_BASE}/{project.id}/finalized_scope.json"
    await azure_blob.upload_bytes(
        json.dumps(cleaned, ensure_ascii=False, indent=2).encode("utf-8"),
        blob_name,
        overwrite=True,
    )
    old_file.file_path = blob_name
    db.add(old_file)
    await db.commit()
    await db.refresh(old_file)

    logger.info(f" Creative finalized_scope.json regenerated for project {project.id}")
    return {**cleaned, "_finalized": True}


async def finalize_scope(
    db: AsyncSession,
    project_id: str,
    scope_data: dict
) -> tuple[models.ProjectFile, dict]:
    """
    Finalize the project scope without LLM — just clean, validate sequencing,
    update metadata, and save finalized_scope.json.
    """

    logger.info(f"Finalizing scope (no LLM) for project {project_id}...")

    # ---- Load project ----
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.company))
        .filter(models.Project.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # ---- Step 1: Clean draft ----
    finalized = await clean_scope(db, scope_data, project=project)
    overview = finalized.get("overview", {})

    # ---- Step 2: Update project metadata ----
    if overview:
        project.name = overview.get("Project Name") or project.name
        project.domain = overview.get("Domain") or project.domain
        project.complexity = overview.get("Complexity") or project.complexity
        project.tech_stack = overview.get("Tech Stack") or project.tech_stack
        project.use_cases = overview.get("Use Cases") or project.use_cases
        project.compliance = overview.get("Compliance") or project.compliance
        project.duration = str(overview.get("Duration") or project.duration)
        await db.commit()
        await db.refresh(project)

    # ---- Step 3: Handle Architecture Diagram ----
    # If the frontend sent back a custom captured image, save it to blob storage
    custom_image_b64 = scope_data.pop("custom_architecture_image", None)
    
    if custom_image_b64 and custom_image_b64.startswith("data:image/png;base64,"):
        try:
            import base64
            logger.info("📸 Saving user-captured React Flow diagram as architecture.png")
            
            # Extract base64 data
            b64_data = custom_image_b64.split(",")[1]
            image_bytes = base64.b64decode(b64_data)
            
            # Save to blob
            blob_path = f"{PROJECTS_BASE}/{project_id}/architecture.png"
            await azure_blob.upload_bytes(image_bytes, blob_path, overwrite=True)
            
            # Ensure DB file record exists
            from app.db.database import get_async_session
            
            arch_result = await db.execute(
                select(models.ProjectFile).filter(
                    models.ProjectFile.project_id == project_id,
                    models.ProjectFile.file_name == "architecture.png"
                )
            )
            arch_file = arch_result.scalars().first()
            if not arch_file:
                arch_file = models.ProjectFile(
                    project_id=project_id,
                    file_name="architecture.png",
                    file_path=blob_path,
                )
                db.add(arch_file)
                await db.commit()
            
            # Update scope with diagram path for presenton.py ONLY iff presenton needs it from scope metadata.
            # actually presenton_client checks os.path or blob for "architecture*"; we will store the path.
            # But wait, frontend wants JSON for the React Flow canvas to still render it!
            # So we keep finalized["architecture_diagram"] as the JSON object.
        except Exception as e:
            logger.error(f"❌ Failed to save custom architecture image: {e}")

    # Generate Architecture Diagram (Deterministic) ONLY if we don't already have one in the scope
    # (otherwise we would overwrite user's React Flow drag & drop changes)
    if "architecture_diagram" not in finalized or not finalized["architecture_diagram"]:
        logger.info("📐 Triggering architecture diagram generation...")
        try:
            # Fetch RFP content from project files
            input_files = [
                {"file_path": f.file_path, "file_name": f.file_name}
                for f in project.files
                if f.file_name not in ["scope.json", "finalized_scope.json", "questions.json", "architecture.png", "architecture.svg"]
                and not f.file_name.startswith("architecture_")
            ]
            
            if input_files:
                rfp_text = await extract_text_from_files(input_files)
                if rfp_text:
                    # Retrieve context
                    kb_chunks = _rag_retrieve(rfp_text[:1000])
                    blob_base_path = f"{PROJECTS_BASE}/{project_id}"
                    
                    # Retrieve and inject path
                    arch_result = await generate_architecture(db, project, rfp_text, kb_chunks, blob_base_path)
                    if arch_result and len(arch_result) > 1 and arch_result[1]:
                        finalized["architecture_diagram"] = arch_result[1]
                        logger.info(f"✅ Injected React Flow architecture JSON into scope")

        except Exception as e:
            logger.error(f"❌ Failed to generate architecture during finalization: {e}")
            # non-blocking error for finalization
    else:
        logger.info("✅ Architecture diagram JSON already present, skipping generation to preserve user edits.")

    # ---- Step 4: Save finalized_scope.json ----
    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
    )
    old_file = result.scalars().first()
    if old_file:
        logger.info(f" Overwriting existing finalized_scope.json for project {project_id}")
    else:
        old_file = models.ProjectFile(
            project_id=project_id,
            file_name="finalized_scope.json",
        )

    blob_name = f"{PROJECTS_BASE}/{project_id}/finalized_scope.json"
    
    # Ensure architecture_diagram is preserved in saved JSON
    await azure_blob.upload_bytes(
        json.dumps(finalized, ensure_ascii=False, indent=2).encode("utf-8"),
        blob_name,
        overwrite=True,
    )

    old_file.file_path = blob_name
    db.add(old_file)
    await db.commit()
    await db.refresh(old_file)

    logger.info(f" Finalized scope saved (no LLM) for project {project_id}")
    return old_file, {**finalized, "_finalized": True}


def _apply_closeout_actuals_to_scope(scope: dict, actuals: List[dict]) -> dict:
    """
    Override scope estimates with actual closed-out data.
    Updates:
    1. Resourcing Plan (Effort, Cost)
    2. Activities (Effort, Duration, End Date - scaled by variance)
    3. project_summary (Total Cost)
    """
    if not actuals:
        return scope

    logger.info(f"Applying {len(actuals)} closeout actuals to scope...")
    
    # Create a map of resource_name -> actual_data
    # Use lowercase for case-insensitive matching
    actual_map = {a.resource_name.lower(): a for a in actuals}
    
    # 1. Update Resourcing Plan & Calculate Variance
    resourcing = scope.get("resourcing_plan", [])
    updated_resourcing = []
    
    # Track variance factors per role to apply to activities
    # role -> effort_multiplier (e.g. 1.5 means took 50% longer)
    role_variance = {} 

    for item in resourcing:
        original_role = item.get("Resources") or item.get("Role", "")
        role_key = original_role.lower()
        
        if role_key in actual_map:
            actual = actual_map[role_key]
            
            # Start with existing values
            old_effort = float(item.get("Efforts") or item.get("Effort Months", 0) or 0)
            
            # Get actual effort
            new_effort = float(actual.actual_effort_months or 0)
            new_cost = float(actual.actual_cost or 0)

            # Calculate Variance for activity scaling
            if old_effort > 0 and new_effort > 0:
                variance = new_effort / old_effort
                role_variance[role_key] = variance
                logger.info(f"   Role {original_role}: Effort {old_effort} -> {new_effort} (Variance: {variance:.2f}x)")
            
            # Update Resourcing Plan Item
            item["Efforts"] = new_effort  # Use standard key
            item["Effort Months"] = new_effort # Backward compatibility
            item["Cost"] = new_cost
            
            # Rate might be recalculated for display consistency
            if new_effort > 0:
                 # Try to update standard key first
                 if "Rate/month" in item:
                     item["Rate/month"] = new_cost / new_effort
                 else:
                     item["Rate"] = new_cost / new_effort
            
            # Mark as actual
            item["_is_actual"] = True
            
        updated_resourcing.append(item)
        
    scope["resourcing_plan"] = updated_resourcing
    
    # 2. Update Activities (Time Shift)
    activities = scope.get("activities", [])
    updated_activities = []
    
    for act in activities:
        owner = act.get("Owner", "").lower()
        # Determine variance to apply
        variance = 1.0
        
        if owner in role_variance:
            variance = role_variance[owner]
        else:
            # Check secondary resources
            res_str = str(act.get("Resources", "")).lower()
            # If any of the roles with variance are in the resources string, apply max variance? 
            # Or average? Let's use the first match for simplicity or max variance for conservatism.
            # Let's take the primary resource (owner) variance if available, else 1.0
            # If owner doesn't match, maybe check if any resource matches
            for role, v in role_variance.items():
                 # Simple substring check - might need better tokenization
                if role in res_str:
                    variance = v
                    break
        
        if variance != 1.0:
            # Scale effort
            old_effort_act = float(act.get("Effort Months", 0) or 1.0)
            new_effort_act = round_to_half(old_effort_act * variance)
            act["Effort Months"] = new_effort_act
            
            # Recalculate End Date if Start Date exists
            start_date_str = act.get("Start Date")
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    # Duration in days approx (months * 30)
                    duration_days = int(new_effort_act * 30)
                    new_end_date = start_date + timedelta(days=duration_days)
                    act["End Date"] = new_end_date.strftime("%Y-%m-%d")
                    # logger.info(f"   Activity {act.get('ID')}: {old_effort_act}m -> {new_effort_act}m. End Date shifted to {act['End Date']}")
                except Exception as e:
                    logger.warning(f"Failed to shift date for activity {act.get('ID')}: {e}")
        
        updated_activities.append(act)
        
    scope["activities"] = updated_activities
    
    # 3. Recalculate Total Cost in Overview/Summary
    total_cost = sum(float(item.get("Cost", 0) or 0) for item in updated_resourcing)
    
    if "cost_summary" not in scope:
        scope["cost_summary"] = {}
    
    scope["cost_summary"]["total_cost"] = total_cost
    
    # 4. Recalculate Project Duration in Overview from Activities
    start_dates = [act.get("Start Date") for act in updated_activities if act.get("Start Date")]
    end_dates = [act.get("End Date") for act in updated_activities if act.get("End Date")]
    
    if start_dates and end_dates:
        try:
            min_start = min(datetime.strptime(str(d), "%Y-%m-%d") for d in start_dates)
            max_end = max(datetime.strptime(str(d), "%Y-%m-%d") for d in end_dates)
            
            # Duration in days approx
            duration_days = (max_end - min_start).days
            # Assume 30 days/month
            duration_months = round(max(0.5, duration_days / 30.0), 1)
            
            if "overview" not in scope:
                scope["overview"] = {}
                
            scope["overview"]["Duration"] = f"{duration_months} months"
            logger.info(f"   Recalculated Duration: {duration_months} months (based on activities)")
        except Exception as e:
            logger.warning(f"Failed to recalculate duration: {e}")
    
    return scope