from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.schemas.image import ImageBrief
from app.schemas.product import ProductInfo
from app.schemas.project import ProjectSetup
from app.services.gemini_text_client import GeminiTextClient
from app.services.pipeline_models import KeywordPlan, ProductAnalysis


class GeminiMarketPlanner:
    """Gemini helper for slot-specific market-ready copy/scenario planning."""

    def __init__(self, settings: Settings) -> None:
        self.client = GeminiTextClient(settings)

    async def plan_slot(
        self,
        *,
        project: ProjectSetup,
        product: ProductInfo,
        brief: ImageBrief,
        analysis: ProductAnalysis,
        keyword_plan: KeywordPlan,
        marketplace: str,
    ) -> dict[str, Any]:
        if not self.client.api_key:
            return {}

        explicit = [item for item in brief.emphasis if str(item).strip()]
        system_prompt = (
            "You are a marketplace content strategist for e-commerce product images. "
            "Produce concise, professional, buyer-relevant copy inputs for image generation. "
            "Use only genuine marketplace-ready phrases. Avoid fluff, hype, fake offers, and gibberish. "
            "Do not invent competitor brands. Keep text short enough for clean visual layouts."
        )
        user_prompt = (
            f"Slot: {brief.slot_name}\n"
            f"Marketplace: {marketplace}\n"
            f"Product title: {product.title}\n"
            f"Category: {project.product_category}\n"
            f"Description: {product.short_description}\n"
            f"Brief instructions: {brief.instructions}\n"
            f"User USPs: {', '.join(product.usps) if product.usps else 'n/a'}\n"
            f"User emphasis: {', '.join(explicit) if explicit else 'n/a'}\n"
            f"Keyword plan: primary={keyword_plan.primary}, secondary={keyword_plan.secondary}, visual={keyword_plan.clean_visual}\n"
            f"OpenAI analysis: style={analysis.visual_style}, lighting={analysis.lighting}, composition={analysis.composition}, text_strategy={analysis.text_strategy}\n"
            "Return strict JSON. "
        )

        if brief.slot_name == "key_facts":
            user_prompt += (
                "Keys: callouts (3-4 items). "
                "Each callout must be a clean marketplace-ready phrase, 2-5 words, truthful and visually usable. "
                "Prefer category-specific benefits over generic adjectives."
            )
        elif brief.slot_name == "lifestyle":
            user_prompt += (
                "Keys: scenario (string), callouts (0-3 items). "
                "If user gave a scenario, optimize it into a more market-ready photographic scenario. "
                "If not, create a realistic scenario matching the marketplace and product. "
                "Callouts must be short contextual claims."
            )
        elif brief.slot_name == "usps":
            user_prompt += (
                "Keys: headline (optional string), callouts (1-3 items). "
                "Optimize the user-provided USPs into concise market-ready phrases."
            )
        elif brief.slot_name == "comparison":
            user_prompt += (
                "Keys: comparison_left (2-3 items), comparison_right (2-3 items). "
                "comparison_left should be product strengths. comparison_right should be realistic generic marketplace alternative weaknesses. "
                "No competitor brand names."
            )
        elif brief.slot_name == "cross_selling":
            user_prompt += (
                "Keys: product_labels (1-6 items). "
                "Use user supplied labels if present and normalize them for clean merchandising display."
            )
        elif brief.slot_name == "closing":
            user_prompt += (
                "Keys: closing_line (optional string), headline (optional string). "
                "Create a restrained conversion-oriented closing line only if it improves the layout."
            )
        else:
            return {}

        result = await self.client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_output_tokens=400,
        )
        return result if isinstance(result, dict) else {}
