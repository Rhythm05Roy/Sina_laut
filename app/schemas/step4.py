"""
Request schemas for Step 4 individual image generation routes.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class BaseStep4Request(BaseModel):
    project_id: str = Field(..., description="Project ID from Step 1")
    style_template: str = Field("playful", description="Visual style (playful, modern, minimal)")

class Image1Request(BaseStep4Request):
    """Main Product Image Request"""
    image_url: str = Field(..., description="Data URL or public URL of the main product photo")

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
class RefineBaseRequest(BaseStep4Request):
    feedback: str = Field(..., description="Refinement instructions")

class Image1RefineRequest(Image1Request, RefineBaseRequest):
    pass

class Image2RefineRequest(Image2Request, RefineBaseRequest):
    pass

class Image3RefineRequest(Image3Request, RefineBaseRequest):
    pass

class Image4RefineRequest(Image4Request, RefineBaseRequest):
    pass

class Image5RefineRequest(Image5Request, RefineBaseRequest):
    pass

class Image6RefineRequest(Image6Request, RefineBaseRequest):
    pass

class Image7RefineRequest(Image7Request, RefineBaseRequest):
    pass
