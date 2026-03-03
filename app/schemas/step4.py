"""
Request schemas for Step 4 individual image generation routes.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal

class KeyFactsConfig(BaseModel):
    style_template: Optional[str] = None
    key_facts: Optional[List[str]] = Field(None, min_length=1, max_length=4)
    background_style: Optional[str] = None
    logo_position: Optional[str] = None

class LifestyleConfig(BaseModel):
    style_template: Optional[str] = None
    scenario: Optional[str] = None
    ref_image_url: Optional[str] = None

class UspsConfig(BaseModel):
    style_template: Optional[str] = None
    usps: Optional[List[str]] = Field(None, min_length=1, max_length=4)

class ComparisonConfig(BaseModel):
    style_template: Optional[str] = None
    advantages: Optional[List[str]] = None
    limitations: Optional[List[str]] = None

class CrossSellingConfig(BaseModel):
    style_template: Optional[str] = None
    product_names: Optional[List[str]] = Field(None, min_length=1, max_length=6)

class ClosingConfig(BaseModel):
    style_template: Optional[str] = None
    direction: Optional[Literal["Emotional", "Inspirational", "Brand Storytelling"]] = None
    headline: Optional[str] = None

class MainRefineConfig(BaseModel):
    style_template: Optional[str] = None
    feedback: Optional[str] = None
    image_url: Optional[str] = None

class KeyFactsRefineConfig(KeyFactsConfig):
    feedback: Optional[str] = None

class LifestyleRefineConfig(LifestyleConfig):
    feedback: Optional[str] = None

class UspsRefineConfig(UspsConfig):
    feedback: Optional[str] = None

class ComparisonRefineConfig(ComparisonConfig):
    feedback: Optional[str] = None

class CrossSellingRefineConfig(CrossSellingConfig):
    feedback: Optional[str] = None

class ClosingRefineConfig(ClosingConfig):
    feedback: Optional[str] = None

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
    brandLogoAssetId: Optional[str] = None
    sku: Optional[str] = None
    shortDescription: Optional[str] = None
    brandFontHeading: Optional[str] = None
    brandFontSubheading: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    imagesCreated: Optional[int] = None
    productsOptimized: Optional[int] = None
    image2: Optional[KeyFactsConfig] = Field(None, description="Optional defaults for key-facts generation")
    image3: Optional[LifestyleConfig] = Field(None, description="Optional defaults for lifestyle generation")
    image4: Optional[UspsConfig] = Field(None, description="Optional defaults for USP generation")
    image5: Optional[ComparisonConfig] = Field(None, description="Optional defaults for comparison generation")
    image6: Optional[CrossSellingConfig] = Field(None, description="Optional defaults for cross-selling generation")
    image7: Optional[ClosingConfig] = Field(None, description="Optional defaults for closing generation")
    refine_image1: Optional[MainRefineConfig] = Field(None, description="Optional defaults for main-product refinement")
    refine_image2: Optional[KeyFactsRefineConfig] = Field(None, description="Optional defaults for key-facts refinement")
    refine_image3: Optional[LifestyleRefineConfig] = Field(None, description="Optional defaults for lifestyle refinement")
    refine_image4: Optional[UspsRefineConfig] = Field(None, description="Optional defaults for USP refinement")
    refine_image5: Optional[ComparisonRefineConfig] = Field(None, description="Optional defaults for comparison refinement")
    refine_image6: Optional[CrossSellingRefineConfig] = Field(None, description="Optional defaults for cross-selling refinement")
    refine_image7: Optional[ClosingRefineConfig] = Field(None, description="Optional defaults for closing refinement")

    model_config = ConfigDict(extra="allow")

class BaseStep4Request(BaseModel):
    style_template: str = Field("playful", description="Visual style (playful, modern, minimal)")
    model_config = ConfigDict(extra="allow")

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
    pass

class Image3Request(BaseStep4Request):
    """Lifestyle Image Request"""
    pass

class Image4Request(BaseStep4Request):
    """USP Highlight Image Request"""
    pass

class Image5Request(BaseStep4Request):
    """Comparison Image Request"""
    pass

class Image6Request(BaseStep4Request):
    """Cross-Selling Image Request"""
    pass

class Image7Request(BaseStep4Request):
    """Closing Image Request"""
    pass

# Refinement Requests
class RefineBaseRequest(BaseModel):
    feedback: str = Field(..., description="Refinement instructions")
    model_config = ConfigDict(extra="allow")

class Image1RefineRequest(BaseStep4Request, RefineBaseRequest):
    image_url: Optional[str] = Field(
        None,
        description="Optional new product image source for refinement. If omitted, previous generated context is used."
    )

class Image2RefineRequest(BaseStep4Request, RefineBaseRequest):
    pass

class Image3RefineRequest(BaseStep4Request, RefineBaseRequest):
    pass

class Image4RefineRequest(BaseStep4Request, RefineBaseRequest):
    pass

class Image5RefineRequest(BaseStep4Request, RefineBaseRequest):
    pass

class Image6RefineRequest(BaseStep4Request, RefineBaseRequest):
    pass

class Image7RefineRequest(BaseStep4Request, RefineBaseRequest):
    pass
