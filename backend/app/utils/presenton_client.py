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
        n_slides: int = 10,
        template: str = "general",
        language: str = "English"
    ) -> Dict[str, str]:
        """
        Generate presentation from project scope data using Presenton API.
        Uses docker exec as proxy since backend runs outside Docker and Presenton binds to localhost.
        
        Args:
            scope_data: Project scope dictionary
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
        # Format scope data as content string
        content = self._format_scope_for_presenton(scope_data)
        
        logger.info(f"Generating presentation with Presenton: {n_slides} slides, template={template}")
        
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
            "enable_images": False,
            "image_provider": "azureopenai"
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
                timeout=120
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
    
    def _format_scope_for_presenton(self, scope: Dict[str, Any]) -> str:
        """
        Convert project scope JSON to Presenton-friendly text format.
        
        Args:
            scope: Project scope dictionary
        
        Returns:
            Formatted text content for Presenton
        """
        lines = []
        
        # Project overview
        if overview := scope.get("overview"):
            project_name = overview.get("Project Name", "Project Presentation")
            lines.append(f"# {project_name}")
            
            if description := overview.get("Description"):
                lines.append(f"\n{description}")
            
            if domain := overview.get("Domain"):
                lines.append(f"\n**Domain:** {domain}")
            
            if tech_stack := overview.get("Tech Stack"):
                lines.append(f"\n**Technology:** {tech_stack}")
        
        # Project summary
        if summary := scope.get("project_summary"):
            lines.append("\n## Project Summary")
            if isinstance(summary, dict):
                for key, value in summary.items():
                    if value:
                        lines.append(f"\n**{key}:** {value}")
            else:
                lines.append(f"\n{summary}")
        
        # Activities
        if activities := scope.get("activities"):
            lines.append("\n## Key Activities")
            if isinstance(activities, list):
                for i, activity in enumerate(activities[:8], 1):  # Top 8 activities
                    if isinstance(activity, dict):
                        activity_name = activity.get("Activity", activity.get("activity", ""))
                        if activity_name:
                            lines.append(f"{i}. {activity_name}")
                    else:
                        lines.append(f"{i}. {activity}")
        
        # Resourcing plan
        if resourcing := scope.get("resourcing_plan"):
            lines.append("\n## Team & Resources")
            if isinstance(resourcing, list):
                for resource in resourcing[:5]:  # Top 5 resources
                    if isinstance(resource, dict):
                        role = resource.get("Resources", resource.get("role", ""))
                        if role:
                            lines.append(f"- {role}")
        
        # Architecture diagram note
        if arch_diagram := scope.get("architecture_diagram"):
            lines.append("\n## Architecture")
            lines.append("System architecture diagram available in project files.")
        
        return "\n".join(lines)
    
    def get_external_url(self) -> str:
        """Get the external URL for accessing Presenton UI"""
        return PRESENTON_EXTERNAL_URL
    
    def get_edit_url(self, presentation_id: str) -> str:
        """Get the full external URL to edit a presentation"""
        return f"{PRESENTON_EXTERNAL_URL}/presentation?id={presentation_id}"


# Singleton instance
presenton_client = PresentonClient()
