from __future__ import annotations
from typing import Optional

from app.core.config import Settings
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.services.openai_text_client import OpenAITextClient


class PromptAnalyzer:
    """
    Lightweight image understanding via OpenAI vision to enrich downstream prompts.
    Takes the uploaded product photo plus structured context and returns a short
    guidance snippet that we prepend to the generative prompt.
    """

    def __init__(self, settings: Settings):
        self.client = OpenAITextClient(settings)

    async def analyze(
        self,
        image_url: str,
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        slot_name: str,
    ) -> Optional[str]:
        if not self.client.api_key or not image_url:
            return None

        system_prompt = (
            "You are an expert marketplace image art director. "
            "Analyze the provided product photo plus context and return a concise "
            "visual guidance block under 120 words to improve the next AI-rendered image. "
            "Focus on composition cues, lighting, surface details, brand/logo handling, and what to avoid. "
            "Do not use bullets or JSON."
        )

        user_prompt = (
            f"Slot: {slot_name}\n"
            f"Brand: {project.brand_name}\n"
            f"Product: {product.title}\n"
            f"Category: {project.product_category}\n"
            f"USPs: {', '.join(product.usps) if product.usps else 'n/a'}\n"
            f"Desired brand palette: {brand.primary_color}/{brand.secondary_color}.\n"
            "Return one short paragraph of practical visual direction."
        )

        return await self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_url=image_url,
            temperature=0.4,
            max_output_tokens=180,
        )
