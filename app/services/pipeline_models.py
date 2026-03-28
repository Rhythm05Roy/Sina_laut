from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProviderHealth(BaseModel):
    openai_image_ready: bool = False
    openai_analysis_ready: bool = False
    gemini_keywords_ready: bool = False
    dataforseo_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)


class ProductAnalysis(BaseModel):
    visual_style: str = ""
    lighting: str = ""
    background: str = ""
    composition: str = ""
    must_avoid: list[str] = Field(default_factory=list)
    usp_visual_strategy: dict[str, str] = Field(default_factory=dict)
    logo_strategy: str = ""
    text_strategy: str = ""
    quality_notes: list[str] = Field(default_factory=list)


class KeywordPlan(BaseModel):
    available: bool = False
    source: Literal["gemini", "dataforseo", "fallback", "none"] = "none"
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    clean_visual: list[str] = Field(default_factory=list)
    warning: Optional[str] = None


class SlotCopyPlan(BaseModel):
    overlay_enabled: bool = False
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    scenario: Optional[str] = None
    callouts: list[str] = Field(default_factory=list)
    comparison_left: list[str] = Field(default_factory=list)
    comparison_right: list[str] = Field(default_factory=list)
    product_labels: list[str] = Field(default_factory=list)
    closing_line: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class CompositionPlan(BaseModel):
    layout: str
    reserved_regions: list[str] = Field(default_factory=list)
    max_text_items: int = 0
    card_style: str = "none"
    text_alignment: str = "left"


class SlotVisualPlan(BaseModel):
    slot_name: str
    image_type: str
    background: str
    composition: str
    text_allowed: bool = False
    logo_allowed: bool = False
    composition_plan: CompositionPlan
    must_avoid: list[str] = Field(default_factory=list)


class SlotPlan(BaseModel):
    slot_name: str
    analysis: ProductAnalysis
    keyword_plan: KeywordPlan
    copy_plan: SlotCopyPlan
    visual_plan: SlotVisualPlan
    generation_prompt: str


class QAReview(BaseModel):
    score: float = 1.0
    issues: list[str] = Field(default_factory=list)
    suggestion: str = ""
