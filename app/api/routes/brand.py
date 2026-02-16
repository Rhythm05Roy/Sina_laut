"""
Step 2 — Brand CI API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4

from app.schemas.brand import BrandCI
from app.core.store import brands, projects, get_brand_by_project_id

router = APIRouter(prefix="/step2/brand", tags=["Step 2 — Brand CI"])

class BrandCreateRequest(BaseModel):
    project_id: str = Field(..., description="Project ID from Step 1")
    brand: BrandCI

class BrandResponse(BrandCI):
    id: str
    project_id: str
    message: str = "Brand CI saved. Proceed to Step 3."

@router.post(
    "/save",
    response_model=BrandResponse,
    status_code=201,
    summary="Save Brand CI",
    description="Step 2: Configure brand identity for a project.",
)
async def save_brand(payload: BrandCreateRequest) -> BrandResponse:
    # Verify project exists
    if payload.project_id not in projects:
        raise HTTPException(status_code=404, detail="Project ID not found. Complete Step 1 first.")

    brand_id = str(uuid4())
    data = {
        "id": brand_id,
        "project_id": payload.project_id,
        **payload.brand.model_dump(),
    }
    # Save to shared store
    brands[brand_id] = data
    return BrandResponse(**data)

@router.get(
    "/project/{project_id}",
    response_model=BrandResponse,
    summary="Get Brand by Project",
)
async def get_brand(project_id: str) -> BrandResponse:
    b = get_brand_by_project_id(project_id)
    if not b:
        raise HTTPException(status_code=404, detail="Brand CI not found for this project.")
    return BrandResponse(**b)
