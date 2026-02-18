from __future__ import annotations
import httpx
import logging
from typing import Optional

from app.core.config import Settings
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo

logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """
    Lightweight image understanding via OpenAI to enrich downstream prompts.
    Takes the uploaded product photo plus structured context and returns a short
    guidance snippet that we prepend to the generative prompt.
    """

    def __init__(self, settings: Settings):
        self.api_key = settings.openai_api_key
        self.model = "gpt-4o-mini"

    async def analyze(
        self,
        image_url: str,
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        slot_name: str,
    ) -> Optional[str]:
        if not self.api_key or not image_url:
            return None

        system_prompt = (
            "You are an expert marketplace image art director. "
            "Analyze the provided product photo plus context and return a concise "
            "visual guidance block (<=120 words) to improve the next AI-rendered image. "
            "Focus on composition cues, lighting, surface details, and what to avoid. "
            "Do NOT include JSON or bullets—plain sentences only."
        )

        user_prompt = (
            f"Slot: {slot_name}\n"
            f"Brand: {project.brand_name}\n"
            f"Product: {product.title}\n"
            f"Category: {project.product_category}\n"
            f"USPs: {', '.join(product.usps) if product.usps else 'n/a'}\n"
            f"Desired style: {brand.primary_color}/{brand.secondary_color} palette, fonts {brand.font_heading}/{brand.font_body}.\n"
            "Return a short guidance paragraph."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": "low"},
                        },
                    ],
                },
            ],
            "max_tokens": 200,
            "temperature": 0.6,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=40) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return content.strip() if content else None
        except Exception as exc:  # pragma: no cover - external call
            logger.warning("OpenAI prompt analysis failed: %s", exc)
            return None
