import json
import logging
import re
from typing import Dict, Any, List

import anyio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import models
from app.engine.prompt_templates import build_architecture_prompt
from app.utils.ai_clients import ollama_chat

logger = logging.getLogger(__name__)

def _extract_json(text: str) -> dict:
    if not text: return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r'```json(.*?)(```|$)', text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except:
            pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0).strip())
        except:
            pass
    return {}

async def generate_architecture(
    db: AsyncSession,
    project,
    rfp_text: str,
    kb_chunks: List[str],
    blob_base_path: str,
) -> tuple[None, dict]:
    """
    Generate structured architecture diagram JSON for React Flow.
    Returns (None, dict_of_nodes_and_edges).
    """

    prompt = build_architecture_prompt(rfp_text, kb_chunks, project)

    logger.info(f"🏗️ Generating structural architecture JSON for project {project.id}...")
    
    async def _generate_json_from_ai(retry: int = 0) -> dict:
        try:
            response_text = await anyio.to_thread.run_sync(
                lambda: ollama_chat(prompt, temperature=0.3, format_json=True)
            )
            return _extract_json(response_text)
        except Exception as e:
            if retry < 2:
                logger.warning(f"AI generation failed (retry {retry+1}): {e}")
                return await _generate_json_from_ai(retry + 1)
            return {}

    arch_json = await _generate_json_from_ai()

    if not arch_json or not any(key in arch_json for key in ["nodes", "edges"]):
        logger.warning("⚠️ Invalid or empty architecture JSON returned for React Flow")
        # Return a safe blank canvas
        return None, {"nodes": [], "edges": []}

    logger.info(f"✅ Generated React Flow JSON ({len(arch_json.get('nodes', []))} nodes, {len(arch_json.get('edges', []))} edges)")

    return None, arch_json

