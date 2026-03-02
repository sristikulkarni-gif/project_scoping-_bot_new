import os

SCOPE_ENGINE = 'app/utils/scope_engine.py'
DIAGRAM_GENERATOR = 'app/engine/diagram_generator.py'

with open(SCOPE_ENGINE, 'r') as f:
    lines = f.readlines()

# Extract lines from _generate_dot_from_json to end of generate_architecture
# Based on previous views: 
# Line 925 is def _generate_dot_from_json
# Line 1415 is return db_file_png, full_blob_path
start_line = 924  # 0-indexed
end_line = 1416

diagram_lines = lines[start_line:end_line]

imports = """import json
import logging
import os
import re
import tempfile
from typing import Dict, Any, List

import anyio
import graphviz
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import models
from app.utils import azure_blob
from app.engine.prompt_templates import build_architecture_prompt, build_eraser_architecture_prompt
from app.utils.ollama_client import ollama_chat

logger = logging.getLogger(__name__)

# --- We also need _extract_json for Ollama JSON parsing if not available here
def _extract_json(text: str) -> dict:
    import builtins
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

"""

with open(DIAGRAM_GENERATOR, 'w') as f:
    f.write(imports)
    f.writelines(diagram_lines)

# Now remove the lines from scope_engine.py
new_scope_lines = lines[:start_line] + ["\n"] + lines[end_line:]

# Needs the new import in scope_engine.py
import_str = "from app.engine.diagram_generator import generate_architecture, generate_architecture_eraser\n"

# Insert the import safely near the top
for i, line in enumerate(new_scope_lines):
    if line.startswith("from app.engine.document_processor"):
        new_scope_lines.insert(i + 1, import_str)
        break

with open(SCOPE_ENGINE, 'w') as f:
    f.writelines(new_scope_lines)

print("Extraction successful.")
