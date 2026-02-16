"""
Step 3 — Product Information API routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List
from uuid import uuid4

from app.schemas.product import ProductInfo
from app.core.store import products, projects, get_product_by_project_id

router = APIRouter(prefix="/step3/product", tags=["Step 3 — Product Info"])

class ProductCreateRequest(BaseModel):
    project_id: str = Field(..., description="ID of the project this product belongs to")
    product: ProductInfo

class ProductResponse(ProductInfo):
    id: str
    project_id: str
    message: str = "Product info saved successfully. Proceed to Step 4."

@router.post(
    "/save",
    response_model=ProductResponse,
    status_code=201,
    summary="Save product information",
    description=(
        "Save product details including SKU, title, description, USPs, "
        "SEO keywords, and target languages. "
        "This corresponds to Step 3 of the wizard."
    ),
)
async def save_product(payload: ProductCreateRequest) -> ProductResponse:
    if payload.project_id not in projects:
        raise HTTPException(status_code=404, detail="Project ID not found")
        
    product_id = str(uuid4())
    data = {
        "id": product_id,
        "project_id": payload.project_id,
        **payload.product.model_dump(),
    }
    products[product_id] = data
    return ProductResponse(**data)

@router.get(
    "/project/{project_id}",
    response_model=ProductResponse,
    summary="Get product by project ID",
    description="Retrieve product information associated with a project.",
)
async def get_product(project_id: str) -> ProductResponse:
    p = get_product_by_project_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found for this project")
    return ProductResponse(**p)
