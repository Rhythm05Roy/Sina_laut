"""
Step 1 — Project Setup API routes.
Manages project creation, retrieval, and updates.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import uuid4

from app.schemas.project import ProjectSetup, Marketplace

router = APIRouter(prefix="/project", tags=["Step 1 — Project Setup"])

# In-memory store (swap for DB in production)
_projects: Dict[str, dict] = {}


class ProjectCreateResponse(BaseModel):
    id: str
    project_name: str
    brand_name: str
    product_category: str
    target_marketplaces: List[Marketplace]
    message: str = "Project created successfully"


class ProjectListResponse(BaseModel):
    projects: List[ProjectCreateResponse]
    total: int


@router.post(
    "/create",
    response_model=ProjectCreateResponse,
    status_code=201,
    summary="Create a new project",
    description=(
        "Creates a new image generation project with brand name, category, and target marketplaces. "
        "This is the first step in the wizard flow."
    ),
)
async def create_project(payload: ProjectSetup) -> ProjectCreateResponse:
    project_id = str(uuid4())
    _projects[project_id] = {
        "id": project_id,
        **payload.model_dump(),
    }
    return ProjectCreateResponse(id=project_id, **payload.model_dump())


@router.get(
    "/{project_id}",
    response_model=ProjectCreateResponse,
    summary="Get project by ID",
    description="Retrieve a project's configuration by its unique ID.",
)
async def get_project(project_id: str) -> ProjectCreateResponse:
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectCreateResponse(**project)


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Retrieve all projects in the system.",
)
async def list_projects() -> ProjectListResponse:
    projects = [ProjectCreateResponse(**p) for p in _projects.values()]
    return ProjectListResponse(projects=projects, total=len(projects))
