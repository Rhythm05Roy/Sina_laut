from __future__ import annotations
from typing import Optional, Dict, Any

from app.core.config import Settings
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.services.openai_text_client import OpenAITextClient


class ProductAnalyst:
    """
    Agent 1 - Product Analyst
    Analyzes product + marketplace context and returns a structured analysis
    describing style, lighting, background, composition, and USP handling.
    """

    def __init__(self, settings: Settings):
        self.client = OpenAITextClient(settings)

    async def run(
        self,
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        marketplace: str = "amazon",
        image_url: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.client.api_key:
            return None

        sys = (
            "Act as an e-commerce product image director for Amazon and similar marketplaces. "
            "Before writing prompts, produce a concise JSON analysis of the best visual strategy. "
            "Consider: marketplace compliance, visual expectations, lighting, composition, which "
            "USPs should be shown visually vs textually, and what to avoid."
        )

        user = (
            f"Product: {product.title}\n"
            f"Category: {project.product_category}\n"
            f"Brand: {project.brand_name}\n"
            f"USPs: {', '.join(product.usps) if product.usps else 'n/a'}\n"
            f"Marketplace: {marketplace}\n"
            "Return JSON with keys: visual_style, lighting, background, composition, must_avoid (list), "
            "usp_visual_strategy (object USP->visual idea). Keep values short and practical."
        )

        return await self.client.generate_json(
            system_prompt=sys,
            user_prompt=user,
            image_url=image_url,
            temperature=0.5,
            max_output_tokens=400,
        )
