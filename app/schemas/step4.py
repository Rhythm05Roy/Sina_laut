"""
Request schemas for Step 4 individual image generation routes.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal

class ExternalProjectPayload(BaseModel):
    """
    Project payload accepted from external backend integrations.
    """
    name: Optional[str] = None
    brandName: Optional[str] = None
    productCategory: Optional[str] = None
    targetMarketplace: Optional[str] = "OTHER"
    status: Optional[str] = None
    mainImage: Optional[str] = None
    brandLogo: Optional[str] = None
    sku: Optional[str] = None
    shortDescription: Optional[str] = None
    brandFontHeading: Optional[str] = None
    brandFontSubheading: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    imagesCreated: Optional[int] = None
    productsOptimized: Optional[int] = None

    model_config = ConfigDict(extra="allow")

class BaseStep4Request(BaseModel):
    style_template: str = Field("playful", description="Visual style (playful, modern, minimal)")
    model_config = ConfigDict(extra="ignore")

class Image1Request(BaseStep4Request):
    """Main Product Image Request"""
    project: Optional[ExternalProjectPayload] = Field(
        None,
        description="External project payload from integration backend."
    )
    image_url: Optional[str] = Field(
        None,
        description="Data URL, public URL, or local file path of the main product photo."
    )
    model_config = ConfigDict(extra="allow")

class Image2Request(BaseStep4Request):
    """Key Facts Image Request"""
    key_facts: List[str] = Field(..., min_length=1, max_length=4, description="List of 4 key facts")
    background_style: str = Field("Minimal", description="Background style for infographic")
    logo_position: str = Field("Top", description="Brand logo position")

class Image3Request(BaseStep4Request):
    """Lifestyle Image Request"""
    scenario: str = Field(..., description="Description of the lifestyle scenario")
    ref_image_url: Optional[str] = Field(None, description="Optional reference image URL")

class Image4Request(BaseStep4Request):
    """USP Highlight Image Request"""
    usps: List[str] = Field(..., min_length=1, max_length=4, description="List of 4 USPs")

class Image5Request(BaseStep4Request):
    """Comparison Image Request"""
    advantages: List[str] = Field(..., description="List of advantages (Our Product)")
    limitations: List[str] = Field(..., description="List of limitations (Other Products)")

class Image6Request(BaseStep4Request):
    """Cross-Selling Image Request"""
    product_names: List[str] = Field(..., min_length=1, max_length=6, description="List of related product names")

class Image7Request(BaseStep4Request):
    """Closing Image Request"""
    direction: Literal["Emotional", "Inspirational", "Brand Storytelling"] = "Emotional"
    headline: Optional[str] = Field(None, description="Optional custom headline")

# Refinement Requests
class RefineBaseRequest(BaseModel):
    feedback: str = Field(..., description="Refinement instructions")
    model_config = ConfigDict(extra="ignore")

class Image1RefineRequest(BaseStep4Request, RefineBaseRequest):
    image_url: Optional[str] = Field(
        None,
        description="Optional new product image source for refinement. If omitted, previous generated context is used."
    )

class Image2RefineRequest(BaseStep4Request, RefineBaseRequest):
    key_facts: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=4,
        description="Optional key facts override for this refinement."
    )
    background_style: Optional[str] = Field(None, description="Optional background style override")
    logo_position: Optional[str] = Field(None, description="Optional logo position override")

class Image3RefineRequest(BaseStep4Request, RefineBaseRequest):
    scenario: Optional[str] = Field(None, description="Optional scenario override")
    ref_image_url: Optional[str] = Field(None, description="Optional reference image URL override")

class Image4RefineRequest(BaseStep4Request, RefineBaseRequest):
    usps: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=4,
        description="Optional USP list override for this refinement."
    )

class Image5RefineRequest(BaseStep4Request, RefineBaseRequest):
    advantages: Optional[List[str]] = Field(None, description="Optional advantages override")
    limitations: Optional[List[str]] = Field(None, description="Optional limitations override")

class Image6RefineRequest(BaseStep4Request, RefineBaseRequest):
    product_names: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=6,
        description="Optional related product names override."
    )

class Image7RefineRequest(BaseStep4Request, RefineBaseRequest):
    direction: Optional[Literal["Emotional", "Inspirational", "Brand Storytelling"]] = None
    headline: Optional[str] = Field(None, description="Optional custom headline override")
