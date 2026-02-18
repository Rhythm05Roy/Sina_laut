from __future__ import annotations
import httpx
import logging
from typing import Optional, Dict, Any

from app.core.config import Settings
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo

logger = logging.getLogger(__name__)


class ProductAnalyst:
    """
    Agent 1 — Product Analyst
    Analyzes product + marketplace context and returns a structured analysis
    describing style, lighting, background, composition, and USP handling.
    """

    def __init__(self, settings: Settings):
        self.api_key = settings.openai_api_key
        self.model = "gpt-4o-mini"

    async def run(
        self,
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        marketplace: str = "amazon",
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        sys = (
            "Act as an e-commerce product image director for Amazon and similar marketplaces. "
            "Before writing prompts, produce a concise JSON analysis of the best visual strategy. "
            "Consider: marketplace compliance (white background for main), visual expectations "
            "(budget vs premium), lighting, composition, which USPs to show visually vs text, "
            "and what to avoid."
        )

        user = (
            f"Product: {product.title}\n"
            f"Category: {project.product_category}\n"
            f"Brand: {project.brand_name}\n"
            f"USPs: {', '.join(product.usps) if product.usps else 'n/a'}\n"
            f"Marketplace: {marketplace}\n"
            "Return JSON with keys: visual_style, lighting, background, composition, must_avoid (list), "
            "usp_visual_strategy (object USP->visual idea). Keep values short."
        )

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            "max_tokens": 400,
            "temperature": 0.5,
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
            import json
            return json.loads(content) if content else None
        except Exception as exc:  # pragma: no cover - external
            logger.warning("ProductAnalyst failed: %s", exc)
            return None
