from pydantic import BaseModel, Field
from typing import List
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief
from app.schemas.style_template import StyleTemplate


class Asset(BaseModel):
    type: str = Field(..., example="product_photo")
    url: str = Field(..., description="Image URL or data URL", min_length=1)


class ImageGenerationRequest(BaseModel):
    project: ProjectSetup
    brand: BrandCI
    product: ProductInfo
    assets: List[Asset] = Field(default_factory=list)
    image_briefs: List[ImageBrief] = Field(..., min_length=1)
    remove_background: bool = True
    style_template: StyleTemplate = Field(
        default=StyleTemplate.PLAYFUL,
        description="Visual style template to apply (playful, modern, minimal)"
    )


class GenerationResponse(BaseModel):
    job_id: str
    status: str
