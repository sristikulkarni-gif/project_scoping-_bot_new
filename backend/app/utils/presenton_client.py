"""
Presenton API Client for integration with Presenton presentation generator.
"""
import httpx
from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

# Presenton service URL
# Note: Using localhost since backend runs outside Docker
# If backend moves to Docker, change to: http://presenton:3000
PRESENTON_BASE_URL = "http://localhost:5000"
# External URL for user access
PRESENTON_EXTERNAL_URL = "http://localhost:5000"


class PresentonClient:
    """Client for interacting with Presenton API"""
    
    def __init__(self, base_url: str = PRESENTON_BASE_URL):
        self.base_url = base_url
    
    async def health_check(self) -> bool:
        """
        Check if Presenton service is available.
        Since Presenton binds to 127.0.0.1 inside container, we check Docker container status.
        """
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=scopebot-presenton", "--filter", "status=running", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "scopebot-presenton" in result.stdout
        except Exception as e:
            logger.warning(f"Failed to check Presenton container status: {e}")
            return False
    
    async def generate_presentation(
        self,
        scope_data: Dict[str, Any],
        rfp_text: str = "",
        n_slides: int = 10,
        template: str = "general",
        language: str = "English"
    ) -> Dict[str, str]:
        """
        Generate presentation deterministically from project scope data.
        Bypasses the LLM entirely and uses /create -> /update -> /export.
        """
        # Force swift template since we mapped slides specifically to its aesthetic layouts
        template = "swift"
        logger.info(f"Generating deterministic presentation with Presenton: template={template}")
        
        import subprocess
        import tempfile
        import json
        import os
        import math
        import uuid
        from datetime import datetime
        
        try:
            # 1. CREATE PRESENTATION CONTAINER
            create_payload = {
                "content": "Deterministic generation layout map",
                "n_slides": n_slides,
                "language": language,
                "template": template,
                "export_as": "pptx",
                "include_table_of_contents": False,
                "include_title_slide": False
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(create_payload, f)
                temp_create_file = f.name
                
            subprocess.run(
                ["docker", "cp", temp_create_file, "scopebot-presenton:/tmp/presenton_create.json"],
                check=True, capture_output=True
            )
            os.unlink(temp_create_file)
            
            create_result = subprocess.run(
                [
                    "docker", "exec", "scopebot-presenton",
                    "curl", "-s", "-X", "POST",
                    "http://localhost:8000/api/v1/ppt/presentation/create",
                    "-H", "Content-Type: application/json",
                    "-d", "@/tmp/presenton_create.json"
                ],
                capture_output=True, text=True, timeout=60
            )
            
            if create_result.returncode != 0:
                raise Exception(f"Create failed: {create_result.stderr}")
                
            presentation = json.loads(create_result.stdout)
            presentation_id = presentation.get('id')
            if not presentation_id:
                raise Exception(f"Invalid create response: {create_result.stdout}")
                
            logger.info(f"Created presentation container: {presentation_id}")
            
            # 2. BUILD DETERMINISTIC SLIDES
            project_title = scope_data.get("overview", {}).get("Project Name", "Project Scope")
            mapped_slides = self._map_scope_to_slides(presentation_id, scope_data, template)
            
            update_payload = {
                "id": presentation_id,
                "title": project_title,
                "n_slides": len(mapped_slides),
                "slides": mapped_slides
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(update_payload, f)
                temp_update_file = f.name
                
            subprocess.run(
                ["docker", "cp", temp_update_file, "scopebot-presenton:/tmp/presenton_update.json"],
                check=True, capture_output=True
            )
            os.unlink(temp_update_file)
            
            update_result = subprocess.run(
                [
                    "docker", "exec", "scopebot-presenton",
                    "curl", "-s", "-X", "PATCH",
                    "http://localhost:8000/api/v1/ppt/presentation/update",
                    "-H", "Content-Type: application/json",
                    "-d", "@/tmp/presenton_update.json"
                ],
                capture_output=True, text=True, timeout=60
            )
            
            if update_result.returncode != 0:
                raise Exception(f"Update failed: {update_result.stderr}")
                
            # 3. EXPORT PRESENTATION
            export_payload = {
                "id": presentation_id,
                "export_as": "pptx"
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(export_payload, f)
                temp_export_file = f.name
                
            subprocess.run(
                ["docker", "cp", temp_export_file, "scopebot-presenton:/tmp/presenton_export.json"],
                check=True, capture_output=True
            )
            os.unlink(temp_export_file)
            
            export_result = subprocess.run(
                [
                    "docker", "exec", "scopebot-presenton",
                    "curl", "-s", "-X", "POST",
                    "http://localhost:8000/api/v1/ppt/presentation/export",
                    "-H", "Content-Type: application/json",
                    "-d", "@/tmp/presenton_export.json"
                ],
                capture_output=True, text=True, timeout=600
            )
            
            if export_result.returncode != 0:
                raise Exception(f"Export failed: {export_result.stderr}")
                
            response_data = json.loads(export_result.stdout)
            
            # Use original Presenton response structure
            final_response = {
                "presentation_id": presentation_id,
                "path": response_data.get('path', ''),
                "edit_path": response_data.get('edit_path', '')
            }
            
            logger.info(f"✅ Presenton generated deterministic presentation: {presentation_id}")
            return final_response
            
        except Exception as e:
            logger.error(f"Deterministic Presenton generation failed: {e}")
            raise
            
    def _map_scope_to_slides(self, presentation_id: str, scope: Dict[str, Any], layout_group: str) -> list:
        """Deterministically map project scope data directly to aesthetic Swift slide components"""
        import uuid
        slides = []
        slide_index = 0
        from datetime import datetime
        website_domain = "www.scopesolution.com"
        
        def add_slide(layout_id: str, content: dict):
            nonlocal slide_index
            slides.append({
                "id": str(uuid.uuid4()),
                "presentation": presentation_id,
                "layout_group": layout_group,
                "layout": f"{layout_group}:{layout_id}",
                "index": slide_index,
                "content": content
            })
            slide_index += 1
            
        # 1. INTRO SLIDE (swift:IntroSlideLayout)
        project_name = scope.get("overview", {}).get("Project Name", "Project Outline")
        desc = scope.get("overview", {}).get("Description", "Project Scope Overview")
        add_slide("IntroSlideLayout", {
            "title": project_name,
            "subtitlePrefix": "Project",
            "subtitleAccent": "Scope",
            "paragraph": desc[:200] if len(desc) > 200 else desc,
            "website": website_domain,
            "introCard": {
                "enabled": True,
                "name": "Scoping Engine",
                "date": datetime.now().strftime("%b %d, %Y")
            },
            "media": {
                "type": "image",
                "image": {
                    "__image_url__": "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?q=80&w=1200",
                    "__image_prompt__": "Professional consulting overview strategy"
                }
            }
        })
        
        # 2. EXECUTIVE SUMMARY (swift:MetricsNumbers)
        exec_summary = scope.get("executive_summary", "Executive overview mapping strategic goals.")
        domain = scope.get("overview", {}).get("Domain", "Enterprise")
        complexity = scope.get("overview", {}).get("Complexity", "Medium")
        duration = scope.get("overview", {}).get("Duration", "TBD")
        cost = scope.get("total_cost")
        cost_str = f"${cost:,.0f}" if isinstance(cost, (int, float)) else str(cost or "TBD")
        
        if exec_summary:
            add_slide("MetricsNumbers", {
                "title": "Executive Summary",
                "leftTitle": "Project Context\n& High-level Details",
                "leftBody": exec_summary[:220] if len(exec_summary) > 220 else exec_summary,
                "website": website_domain,
                "metrics": [
                    {
                        "value": domain[:8] if len(domain) > 8 else domain,
                        "line1": "Target",
                        "line2": "Domain",
                        "description": f"Domain focus: {domain}".upper()
                    },
                    {
                        "value": complexity[:8],
                        "line1": "Project",
                        "line2": "Complexity",
                        "description": f"Overall delivery difficulty rated as {complexity}"
                    },
                    {
                        "value": cost_str[:8] if len(cost_str) > 5 else cost_str,
                        "line1": "Budget",
                        "line2": "Estimate",
                        "description": f"With an estimated timeline of {duration}"
                    }
                ]
            })

        # 3. KEY OBJECTIVES (swift:image-list-description-slide)
        if objectives := scope.get("objectives"):
            obj_list = objectives if isinstance(objectives, list) else [objectives]
            
            # Map up to 3 objectives max for this layout
            items = []
            for idx, obj in enumerate(obj_list[:3]):
                items.append({
                    "title": f"Objective {idx+1}",
                    "description": obj[:140],
                    "image": {
                        "__image_url__": f"https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=400&sig={idx}",
                        "__image_prompt__": "Strategic goal execution abstract"
                    }
                })
                
            # Fallback if there are less than 3 objectives to satisfy the min constraints of the schema
            while len(items) < 3:
                items.append({
                    "title": "Additional Goal",
                    "description": "System optimization and continued enhancement alignment.",
                    "image": {
                        "__image_url__": f"https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=400",
                        "__image_prompt__": "General target goal"
                    }
                })

            add_slide("image-list-description-slide", {
                "titleLine1": "Project",
                "titleLine2": "Objectives",
                "description": "The primary goals and intended outcomes required for the successful delivery of this engagement.",
                "items": items,
                "website": website_domain
            })

        # 4. ACTIVITIES (swift:Timeline) -> 4 items per page
        if activities := scope.get("activities"):
            act_list = activities if isinstance(activities, list) else []
            chunk_size = 4
            chunks = [act_list[i:i + chunk_size] for i in range(0, len(act_list), chunk_size)]
            
            for i, chunk in enumerate(chunks):
                items = []
                for idx, act in enumerate(chunk):
                    if isinstance(act, dict):
                        name = act.get("Activities", act.get("name", act.get("activity", "Task")))
                        desc = act.get("Deliverable", act.get("deliverable", "Details TBD"))
                        effort = act.get("Effort (Months)", act.get("effort", ""))
                        if effort:
                            desc = f"{effort} months. {desc}"
                    else:
                        name = str(act)
                        desc = "Activity detail"
                        
                    items.append({
                        "year": f"P{i*chunk_size + idx + 1}", # Phase/Num
                        "heading": name[:28],
                        "body": desc[:160],
                        "icon": {"__icon_url__": "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/clipboard-text-bold.svg", "__icon_query__": "timeline phase"}
                    })
                    
                add_slide("Timeline", {
                    "title": f"Detailed Roadmap{f' ({i+1})' if len(chunks)>1 else ''}",
                    "subtitle": "Breakdown of the core phases, expected activities, and deliverables mapped sequentially.",
                    "items": items,
                    "website": website_domain
                })

        # 5. TEAM & RESOURCES (swift:SwiftTableOfContents) -> 10 items max
        if resourcing := scope.get("resourcing_plan"):
            if isinstance(resourcing, list):
                chunk_size = 10
                chunks = [resourcing[i:i + chunk_size] for i in range(0, len(resourcing), chunk_size)]
                
                for i, chunk in enumerate(chunks):
                    items = []
                    for res in chunk:
                        if isinstance(res, dict):
                            role = res.get("Resources", res.get("role", "Resource"))
                            effort = res.get("Effort (Months)", res.get("effort", ""))
                            items.append({
                                "title": f"{role} ({effort}m)"[:40],
                                "description": "Required project allocation"
                            })
                            
                    if items:
                        add_slide("SwiftTableOfContents", {
                            "title": f"Team Requirements{f' ({i+1})' if len(chunks)>1 else ''}",
                            "items": items,
                            "website": website_domain
                        })

        return slides

    def get_external_url(self) -> str:
        """Get the external URL for accessing Presenton UI"""
        return PRESENTON_EXTERNAL_URL
    
    def get_edit_url(self, presentation_id: str) -> str:
        """Get the full external URL to edit a presentation"""
        return f"{PRESENTON_EXTERNAL_URL}/presentation?id={presentation_id}"


# Singleton instance
presenton_client = PresentonClient()
