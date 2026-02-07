from pydantic import BaseModel, Field, HttpUrl
from typing import List
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief

class Asset(BaseModel):
    type: str = Field(..., example="product_photo")
    url: HttpUrl

class ImageGenerationRequest(BaseModel):
    project: ProjectSetup
    brand: BrandCI
    product: ProductInfo
    assets: List[Asset] = Field(default_factory=list)
    image_briefs: List[ImageBrief] = Field(..., min_items=1)
    remove_background: bool = True

class GenerationResponse(BaseModel):
    job_id: str
    status: str
