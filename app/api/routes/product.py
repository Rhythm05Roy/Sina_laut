"""
Step 3 — Product Information API routes.
Manages product details: SKU, title, description, USPs, keywords, languages.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import uuid4

from app.schemas.product import ProductInfo

router = APIRouter(prefix="/product", tags=["Step 3 — Product Info"])

# In-memory store
_products: Dict[str, dict] = {}


class ProductCreateRequest(BaseModel):
    project_id: str = Field(..., description="ID of the project this product belongs to")
    product: ProductInfo


class ProductResponse(BaseModel):
    id: str
    project_id: str
    sku: str
    title: str
    short_description: str
    usps: List[str] = []
    keywords: Dict[str, List[str]] = {}
    languages: List[str] = ["en"]
    message: str = "Product info saved successfully"


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
    product_id = str(uuid4())
    data = {
        "id": product_id,
        "project_id": payload.project_id,
        **payload.product.model_dump(),
    }
    _products[product_id] = data
    return ProductResponse(**data)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Retrieve product information by product ID.",
)
async def get_product(product_id: str) -> ProductResponse:
    product = _products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(**product)


@router.get(
    "/project/{project_id}",
    response_model=ProductResponse,
    summary="Get product by project ID",
    description="Retrieve product information associated with a project.",
)
async def get_product_by_project(project_id: str) -> ProductResponse:
    for product in _products.values():
        if product["project_id"] == project_id:
            return ProductResponse(**product)
    raise HTTPException(status_code=404, detail="Product not found for this project")
