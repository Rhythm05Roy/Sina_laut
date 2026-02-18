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
    suggested_prompts: dict | None = Field(
        default=None,
        description="Optional prompt suggestions for downstream slots (key_facts, lifestyle, etc.)"
    )
    analysis_used: bool | None = Field(
        default=None,
        description="Whether OpenAI vision analysis was attempted for this request."
    )
    analysis_ok: bool | None = Field(
        default=None,
        description="Whether vision analysis succeeded."
    )
    analysis_text: str | None = Field(
        default=None,
        description="Guidance text produced by vision analysis (if available)."
    )
    placeholder_used: bool | None = Field(
        default=None,
        description="True if a placeholder image was returned instead of a real generation."
    )
    error: str | None = Field(
        default=None,
        description="Optional error/warning message from the generation step."
    )
