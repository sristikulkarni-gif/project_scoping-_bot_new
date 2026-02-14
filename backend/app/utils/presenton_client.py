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
        Generate presentation from project scope data using Presenton API.
        Uses docker exec as proxy since backend runs outside Docker and Presenton binds to localhost.
        
        Args:
            scope_data: Project scope dictionary
            rfp_text: Original RFP/requirements text for full context
            n_slides: Number of slides to generate
            template: Template name (e.g., "general", "business", "tech")
            language: Presentation language
        
        Returns:
            Dictionary with:
                - presentation_id: UUID of generated presentation
                - path: File path to generated PPTX
                - edit_path: URL path to edit in Presenton UI
        
        Raises:
            Exception: If generation fails
        """
        # Format scope data as content string with RFP context
        content = self._format_scope_for_presenton(scope_data, rfp_text)
        
        logger.info(f"Generating presentation with Presenton: {n_slides} slides, template={template}")
        logger.info(f"📊 Content length: {len(content)} chars (RFP: {len(rfp_text)} chars)")
        
        # Create request payload
        payload = {
            "content": content,
            "n_slides": n_slides,
            "language": language,
            "template": template,
            "export_as": "pptx",
            # Explicitly specify Azure OpenAI to override default Google Gemini
            "llm_provider": "azureopenai",
            "llm_model": "gpt-4o",
            "enable_images": True,
            "image_provider": "dall-e-3"
        }

        
        # Use docker exec to make request from inside container
        import subprocess
        import tempfile
        
        try:
            # Write payload to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(payload, f)
                temp_file = f.name
            
            # Copy payload into container
            subprocess.run(
                ["docker", "cp", temp_file, "scopebot-presenton:/tmp/presenton_request.json"],
                check=True,
                capture_output=True
            )
            
            # Make request from inside container using curl
            result = subprocess.run(
                [
                    "docker", "exec", "scopebot-presenton",
                    "curl", "-s", "-X", "POST",
                    "http://localhost:8000/api/v1/ppt/presentation/generate",
                    "-H", "Content-Type: application/json",
                    "-d", f"@/tmp/presenton_request.json"
                ],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Clean up temp file
            import os
            os.unlink(temp_file)
            
            if result.returncode != 0:
                raise Exception(f"Docker exec failed: {result.stderr}")
            
            response_data = json.loads(result.stdout)
            logger.info(f"✅ Presenton generated presentation: {response_data.get('presentation_id')}")
            return response_data
            
        except Exception as e:
            logger.error(f"Presenton generation failed: {e}")
            raise
    
    def _format_scope_for_presenton(self, scope: Dict[str, Any], rfp_text: str = "") -> str:
        """
        Convert project scope JSON to Presenton-friendly text format.
        Includes original RFP content for full context.
        
        Args:
            scope: Project scope dictionary
            rfp_text: Original RFP/requirements document text
        
        Returns:
            Formatted text content for Presenton
        """
        lines = []
        
        # ===== SECTION 1: Original RFP Content =====
        if rfp_text:
            lines.append("# Original Requirements & Context")
            lines.append("\n## Source Document")
            # Limit RFP to reasonable size (first 8000 chars ≈ 2000 words)
            rfp_preview = rfp_text[:8000]
            if len(rfp_text) > 8000:
                rfp_preview += "\n\n[... document continues ...]"
            lines.append(f"\n{rfp_preview}")
            lines.append("\n---\n")
        
        # ===== SECTION 2: Project Overview =====
        if overview := scope.get("overview"):
            project_name = overview.get("Project Name", "Project Presentation")
            lines.append(f"# {project_name}")
            
            if description := overview.get("Description"):
                lines.append(f"\n{description}")
            
            if domain := overview.get("Domain"):
                lines.append(f"\n**Domain:** {domain}")
            
            if tech_stack := overview.get("Tech Stack"):
                lines.append(f"\n**Technology Stack:** {tech_stack}")
            
            if complexity := overview.get("Complexity"):
                lines.append(f"\n**Complexity:** {complexity}")
            
            if duration := overview.get("Duration"):
                lines.append(f"\n**Duration:** {duration}")
            
            if use_cases := overview.get("Use Cases"):
                lines.append(f"\n**Use Cases:** {use_cases}")
            
            if compliance := overview.get("Compliance"):
                lines.append(f"\n**Compliance:** {compliance}")
        
        # ===== SECTION 3: Executive Summary =====
        if exec_summary := scope.get("executive_summary"):
            lines.append("\n## Executive Summary")
            lines.append(f"\n{exec_summary}")
        
        # ===== SECTION 4: Project Summary =====
        if summary := scope.get("project_summary"):
            lines.append("\n## Project Summary")
            if isinstance(summary, dict):
                for key, value in summary.items():
                    if value:
                        lines.append(f"\n**{key}:** {value}")
            else:
                lines.append(f"\n{summary}")
        
        # ===== SECTION 5: Objectives =====
        if objectives := scope.get("objectives"):
            lines.append("\n## Objectives")
            if isinstance(objectives, list):
                for obj in objectives:
                    lines.append(f"- {obj}")
            else:
                lines.append(f"\n{objectives}")
        
        # ===== SECTION 6: Key Activities =====
        if activities := scope.get("activities"):
            lines.append("\n## Key Activities & Deliverables")
            if isinstance(activities, list):
                for i, activity in enumerate(activities, 1):
                    if isinstance(activity, dict):
                        activity_name = activity.get("Activity", activity.get("activity", ""))
                        deliverable = activity.get("Deliverable", activity.get("deliverable", ""))
                        effort = activity.get("Effort (Months)", activity.get("effort", ""))
                        
                        if activity_name:
                            lines.append(f"\n### {i}. {activity_name}")
                            if deliverable:
                                lines.append(f"**Deliverable:** {deliverable}")
                            if effort:
                                lines.append(f"**Effort:** {effort} months")
                    else:
                        lines.append(f"{i}. {activity}")
        
        # ===== SECTION 7: Team & Resources =====
        if resourcing := scope.get("resourcing_plan"):
            lines.append("\n## Team & Resources")
            if isinstance(resourcing, list):
                for resource in resourcing:
                    if isinstance(resource, dict):
                        role = resource.get("Resources", resource.get("role", ""))
                        effort = resource.get("Effort (Months)", resource.get("effort", ""))
                        if role:
                            effort_str = f" ({effort} months)" if effort else ""
                            lines.append(f"- {role}{effort_str}")
        
        # ===== SECTION 8: Timeline =====
        if timeline := scope.get("timeline"):
            lines.append("\n## Project Timeline")
            if isinstance(timeline, list):
                for phase in timeline:
                    if isinstance(phase, dict):
                        phase_name = phase.get("Phase", phase.get("phase", ""))
                        start = phase.get("Start Date", phase.get("start", ""))
                        end = phase.get("End Date", phase.get("end", ""))
                        if phase_name:
                            lines.append(f"\n**{phase_name}**")
                            if start and end:
                                lines.append(f"Duration: {start} to {end}")
        
        # ===== SECTION 9: Risks & Mitigation =====
        if risks := scope.get("risks"):
            lines.append("\n## Risks & Mitigation")
            if isinstance(risks, list):
                for risk in risks[:5]:  # Top 5 risks
                    if isinstance(risk, dict):
                        risk_desc = risk.get("Risk", risk.get("risk", ""))
                        mitigation = risk.get("Mitigation", risk.get("mitigation", ""))
                        if risk_desc:
                            lines.append(f"\n**Risk:** {risk_desc}")
                            if mitigation:
                                lines.append(f"**Mitigation:** {mitigation}")
        
        # ===== SECTION 10: Cost Estimate =====
        if cost := scope.get("total_cost"):
            lines.append("\n## Cost Estimate")
            lines.append(f"\n**Total Project Cost:** ${cost:,.2f}" if isinstance(cost, (int, float)) else f"\n**Total Project Cost:** {cost}")
        
        # ===== SECTION 11: Architecture =====
        if arch_diagram := scope.get("architecture_diagram"):
            lines.append("\n## System Architecture")
            lines.append("Detailed architecture diagram available in project documentation.")
        
        return "\n".join(lines)
    
    def get_external_url(self) -> str:
        """Get the external URL for accessing Presenton UI"""
        return PRESENTON_EXTERNAL_URL
    
    def get_edit_url(self, presentation_id: str) -> str:
        """Get the full external URL to edit a presentation"""
        return f"{PRESENTON_EXTERNAL_URL}/presentation?id={presentation_id}"


# Singleton instance
presenton_client = PresentonClient()
