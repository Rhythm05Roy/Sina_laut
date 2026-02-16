"""
Step 1 — Project Setup API routes.
"""
from fastapi import APIRouter, HTTPException
from contextlib import asynccontextmanager
from typing import List, Dict
from uuid import uuid4

from app.schemas.project import ProjectSetup, Marketplace
from app.core.store import projects  # Shared store
from pydantic import BaseModel

# Explicitly named "Step 1" route prefix
router = APIRouter(prefix="/step1/project", tags=["Step 1 — Project Setup"])

class ProjectCreateResponse(ProjectSetup):
    id: str
    message: str = "Project created successfully. Proceed to Step 2."

class ProjectListResponse(BaseModel):
    projects: List[ProjectCreateResponse]
    total: int



@router.post(
    "/create",
    response_model=ProjectCreateResponse,
    status_code=201,
    summary="Create Project",
    description="Step 1: Create a new project. Returns project ID required for subsequent steps.",
)
async def create_project(payload: ProjectSetup) -> ProjectCreateResponse:
    project_id = str(uuid4())
    # Save to shared store
    projects[project_id] = {
        "id": project_id,
        **payload.model_dump(),
    }
    return ProjectCreateResponse(id=project_id, **payload.model_dump())

@router.get(
    "/{project_id}",
    response_model=ProjectCreateResponse,
    summary="Get Project",
)
async def get_project(project_id: str) -> ProjectCreateResponse:
    p = projects.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectCreateResponse(**p)

@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List Projects",
)
async def list_projects() -> ProjectListResponse:
    # Convert dicts back to models
    items = []
    for p in projects.values():
        items.append(ProjectCreateResponse(**p))
    return ProjectListResponse(projects=items, total=len(items))
