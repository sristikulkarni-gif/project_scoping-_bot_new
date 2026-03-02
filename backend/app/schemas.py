from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from fastapi_users import schemas as fa_schemas


# USER SCHEMAS
class UserRead(fa_schemas.BaseUser[uuid.UUID]):
    username: str
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]


class UserCreate(fa_schemas.BaseUserCreate):
    username: str


class UserUpdate(fa_schemas.BaseUserUpdate):
    username: Optional[str] = None


class UserList(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool

    class Config:
        from_attributes = True


# AUTHENTICATION
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# COMPANY + RATE CARD SCHEMAS
class CompanyBase(BaseModel):
    name: str
    currency: Optional[str] = "USD"


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class RateCardBase(BaseModel):
    role_name: str
    monthly_rate: float


class RateCardCreate(RateCardBase):
    pass


class RateCardUpdate(BaseModel):
    monthly_rate: float


class RateCardRead(RateCardBase):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


# PROJECT FILE SCHEMAS
class ProjectFile(BaseModel):
    id: uuid.UUID
    file_name: str
    file_path: str
    uploaded_at: datetime
    download_url: Optional[str] = None
    preview_url: Optional[str] = None

    class Config:
        from_attributes = True


#  PROJECT SCHEMAS
class ProjectBase(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    complexity: Optional[str] = None
    tech_stack: Optional[str] = None
    use_cases: Optional[str] = None
    compliance: Optional[str] = None
    duration: Optional[str] = None


class ProjectCreate(ProjectBase):
    company_id: Optional[uuid.UUID] = None


class Project(ProjectBase):
    id: uuid.UUID
    files: List[ProjectFile] = []
    owner_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    company: Optional[CompanyRead] = None
    created_at: datetime
    updated_at: Optional[datetime]
    has_finalized_scope: bool = False
    status: str = "draft"
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# SCOPE & GENERATION SCHEMAS
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# LLM Structured Output Schemas (for Deterministic Scoping)
# ---------------------------------------------------------

class TechExtractionOutput(BaseModel):
    """Phase 0: Extract explicitly mentioned technologies from RFP."""
    technologies: List[str] = Field(
        description="List of ALL specific technologies, tools, platforms, frameworks, "
        "and services explicitly mentioned in the RFP document. Only include what is "
        "directly stated, not implied. Examples: 'Azure SQL Database', 'Power BI', "
        "'Snowflake', 'Kafka', 'React', 'Terraform'."
    )

class TechItem(BaseModel):
    """An individual technology recommendation."""
    name: str = Field(description="Specific technology name (e.g., 'React 18', 'Azure Data Factory')")
    classification: str = Field(description="Must be exactly 'Explicit' or 'Implicit'")
    justification: str = Field(description="1-2 sentences explaining why this technology is recommended. Mandatory if Implicit.")

class TechCategory(BaseModel):
    """A category of technologies in the recommended tech stack."""
    category: str = Field(description="Category name (e.g., 'Frontend', 'Backend', 'Database', 'Infrastructure', 'AI/ML', 'DevOps')")
    technologies: List[TechItem] = Field(description="List of specific technologies in this category")

class PlanOutput(BaseModel):
    """Phase 1: High-level project plan and team composition."""
    phases: List[str] = Field(description="Names of the high-level project phases, in order (e.g., ['Discovery', 'Design', 'Development', 'Testing'])")
    team_roles: List[str] = Field(description="List of specific roles required for this project, matching the provided rate cards.")
    executive_summary: str = Field(description="A concise executive summary of the project goal.")
    key_deliverables: List[str] = Field(description="List of 3-5 major tangible deliverables.")
    complexity: str = Field(
        default="Medium",
        description="Overall project complexity: must be exactly one of 'Simple', 'Medium', or 'High'. Base this on the number of integrations, team size needed, regulatory requirements, and technical depth."
    )
    complexity_reasoning: str = Field(
        default="",
        description="One sentence explaining why this complexity level was chosen."
    )
    recommended_tech_stack: List[TechCategory] = Field(
        default=[],
        description="Recommended technology stack organized by category. Based on the domain, RFP content, and best practices. Include: Frontend, Backend, Database, Infrastructure, DevOps, and optionally AI/ML or Mobile if relevant."
    )

class ActivityItem(BaseModel):
    """A granular activity belonging to Phase 2 schedule generation."""
    name: str = Field(description="Name of the specific activity/task.")
    phase: str = Field(description="Which phase this belongs to (must match a phase from Phase 1).")
    owner: str = Field(description="The primary role responsible for this task (must match a role from Phase 1).")
    effort_months: float = Field(description="Estimated pure effort required in months (e.g., 0.5 for 2 weeks).")
    dependencies: List[str] = Field(description="Names of other activities that MUST be completed before this one can start. Empty list if none.")

class ScheduleOutput(BaseModel):
    """Phase 2: Granular schedule with dependencies but no math/dates."""
    activities: List[ActivityItem] = Field(description="List of all project activities needed to deliver the project.")


# ---------------------------------------------------------
# API Response Schemas
# ---------------------------------------------------------

class GeneratedScopeResponse(BaseModel):
    overview: Dict[str, Any] = {}
    activities: List[Dict[str, Any]] = []
    resourcing_plan: List[Dict[str, Any]] = []
    architecture_diagram: Optional[Any] = None
    discount_percentage: Optional[float] = None  # Add discount support
    _finalized: Optional[bool] = None


class MessageResponse(BaseModel):
    msg: str
    scope: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    has_finalized_scope: Optional[bool] = None
    architecture_diagram: Optional[Any] = None


class RegenerateScopeRequest(BaseModel):
    draft: Dict[str, Any]
    instructions: str


#  QUESTION GENERATION SCHEMAS
class QuestionItem(BaseModel):
    question: str
    user_understanding: Optional[str] = ""
    comment: Optional[str] = ""


class QuestionCategory(BaseModel):
    category: str
    items: List[QuestionItem]


class GenerateQuestionsResponse(BaseModel):
    msg: str
    questions: List[QuestionCategory]


#  PROMPT HISTORY SCHEMAS
class RoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class PromptBase(BaseModel):
    role: RoleEnum = Field(default=RoleEnum.user, description="Role of the speaker")
    message: str = Field(..., min_length=1, description="Prompt text content")


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    message: str = Field(..., min_length=1)


class PromptRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    role: RoleEnum
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class PromptListResponse(BaseModel):
    prompts: List[PromptRead]

    class Config:
        from_attributes = True


class StatusResponse(BaseModel):
    status: str


# CLOSEOUT SCHEMAS
class ResourceActualInput(BaseModel):
    resource_name: str
    rate_per_month: float
    estimated_effort_months: float
    actual_effort_months: float
    estimated_cost: float
    actual_cost: float
    notes: Optional[str] = None


class CloseProjectRequest(BaseModel):
    actuals: List[ResourceActualInput]



