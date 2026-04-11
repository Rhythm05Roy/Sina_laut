"""
Request schemas for Step 4 individual image generation routes.
"""
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from typing import Any, Dict, List, Optional, Literal


class Step4Schema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class KeyFactsConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    key_facts: Optional[List[str]] = Field(None, alias="keyFacts", min_length=1, max_length=4)
    background_style: Optional[str] = Field(None, alias="backgroundStyle")
    logo_position: Optional[str] = Field(None, alias="logoPosition")
    image_url: Optional[str] = Field(None, alias="imageUrl")


class LifestyleConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    scenario: Optional[str] = None
    ref_image_url: Optional[str] = Field(None, alias="refImageUrl")


class UspsConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    usps: Optional[List[str]] = Field(None, min_length=1, max_length=4)


class ComparisonConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    advantages: Optional[List[str]] = None
    limitations: Optional[List[str]] = None


class CrossSellingConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    product_names: Optional[List[str]] = Field(None, alias="productNames", min_length=1, max_length=6)
    product_urls: Optional[List[str]] = Field(None, alias="productUrls", min_length=1, max_length=6)


class ClosingConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    direction: Optional[Literal["Emotional", "Inspirational", "Brand Storytelling"]] = None
    headline: Optional[str] = None


class MainRefineConfig(Step4Schema):
    style_template: Optional[str] = Field(None, alias="style")
    feedback: Optional[str] = None
    image_url: Optional[str] = Field(None, alias="imageUrl")


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


class ExternalProjectPayload(Step4Schema):
    project_id: Optional[str] = Field(
        None,
        alias="id",
        validation_alias=AliasChoices("id", "projectId"),
    )
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


class BaseStep4Request(Step4Schema):
    style_template: Optional[str] = Field("playful", alias="style")


class ProjectRequestBase(BaseStep4Request):
    project: Optional[ExternalProjectPayload] = None


class ProjectContextRequestBase(BaseStep4Request):
    project_context: Optional[Dict[str, Any]] = Field(None, alias="projectContext")


class Image1Request(ProjectRequestBase):
    image_url: Optional[str] = Field(None, alias="imageUrl")


class Image2Request(BaseStep4Request):
    key_facts: Optional[List[str]] = Field(None, alias="keyFacts", min_length=1, max_length=4)
    background_style: Optional[str] = Field(None, alias="backgroundStyle")
    logo_position: Optional[str] = Field(None, alias="logoPosition")
    image_url: Optional[str] = Field(None, alias="imageUrl")


class Image3Request(BaseStep4Request):
    scenario: Optional[str] = None
    ref_image_url: Optional[str] = Field(None, alias="refImageUrl")


class Image4Request(BaseStep4Request):
    usps: Optional[List[str]] = Field(None, min_length=1, max_length=4)


class Image5Request(BaseStep4Request):
    advantages: Optional[List[str]] = None
    limitations: Optional[List[str]] = None


class Image6Request(BaseStep4Request):
    product_names: Optional[List[str]] = Field(None, alias="productNames", min_length=1, max_length=6)
    product_urls: Optional[List[str]] = Field(None, alias="productUrls", min_length=1, max_length=6)


class Image7Request(BaseStep4Request):
    direction: Optional[str] = None
    headline: Optional[str] = None


class RefineBaseRequest(ProjectContextRequestBase):
    feedback: str = Field(..., description="Refinement instructions")


class Image1RefineRequest(RefineBaseRequest):
    image_url: Optional[str] = Field(None, alias="imageUrl")


class Image2RefineRequest(RefineBaseRequest):
    key_facts: Optional[List[str]] = Field(None, alias="keyFacts", min_length=1, max_length=4)
    background_style: Optional[str] = Field(None, alias="backgroundStyle")
    logo_position: Optional[str] = Field(None, alias="logoPosition")
    image_url: Optional[str] = Field(None, alias="imageUrl")


class Image3RefineRequest(RefineBaseRequest):
    scenario: Optional[str] = None
    ref_image_url: Optional[str] = Field(None, alias="refImageUrl")


class Image4RefineRequest(RefineBaseRequest):
    usps: Optional[List[str]] = Field(None, min_length=1, max_length=4)


class Image5RefineRequest(RefineBaseRequest):
    advantages: Optional[List[str]] = None
    limitations: Optional[List[str]] = None


class Image6RefineRequest(RefineBaseRequest):
    product_names: Optional[List[str]] = Field(None, alias="productNames", min_length=1, max_length=6)
    product_urls: Optional[List[str]] = Field(None, alias="productUrls", min_length=1, max_length=6)


class Image7RefineRequest(RefineBaseRequest):
    direction: Optional[str] = None
    headline: Optional[str] = None
