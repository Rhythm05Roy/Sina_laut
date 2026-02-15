"""
Step 2 — Brand CI (Corporate Identity) API routes.
Manages brand configuration: logo, colors, fonts.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Optional
from uuid import uuid4

from app.schemas.brand import BrandCI

router = APIRouter(prefix="/brand", tags=["Step 2 — Brand CI"])

# In-memory store
_brands: Dict[str, dict] = {}


class BrandCreateRequest(BaseModel):
    project_id: str = Field(..., description="ID of the project this brand belongs to")
    brand: BrandCI


class BrandResponse(BaseModel):
    id: str
    project_id: str
    logo_url: Optional[str] = None
    primary_color: str
    secondary_color: str
    font_heading: str
    font_body: str
    message: str = "Brand CI saved successfully"


@router.post(
    "/save",
    response_model=BrandResponse,
    status_code=201,
    summary="Save brand identity",
    description=(
        "Save or update brand corporate identity settings including logo, "
        "primary/secondary colors, and heading/body fonts. "
        "This corresponds to Step 2 of the wizard."
    ),
)
async def save_brand(payload: BrandCreateRequest) -> BrandResponse:
    brand_id = str(uuid4())
    data = {
        "id": brand_id,
        "project_id": payload.project_id,
        **payload.brand.model_dump(),
    }
    _brands[brand_id] = data
    return BrandResponse(**data)


@router.get(
    "/{brand_id}",
    response_model=BrandResponse,
    summary="Get brand by ID",
    description="Retrieve brand CI settings by brand ID.",
)
async def get_brand(brand_id: str) -> BrandResponse:
    brand = _brands.get(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return BrandResponse(**brand)


@router.get(
    "/project/{project_id}",
    response_model=BrandResponse,
    summary="Get brand by project ID",
    description="Retrieve brand CI settings associated with a project.",
)
async def get_brand_by_project(project_id: str) -> BrandResponse:
    for brand in _brands.values():
        if brand["project_id"] == project_id:
            return BrandResponse(**brand)
    raise HTTPException(status_code=404, detail="Brand not found for this project")
