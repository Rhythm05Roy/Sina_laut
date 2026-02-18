from __future__ import annotations
from typing import Dict, Any, List

from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief
from app.schemas.style_template import StyleTemplate
from app.services.prompt_builder import build_prompt
from app.services.prompt_templates import CATEGORY_TEMPLATES, MARKETPLACE_RULES


class PromptEngineer:
    """
    Agent 3 — Prompt Engineer
    Merges analysis + strategy + base prompt into a concise, Gemini-ready prompt.

    Key principle: Gemini image gen performs best with concise, descriptive prompts.
    We enrich with category and marketplace context but keep total prompt
    under ~800 characters for optimal results.
    """

    @staticmethod
    def compose(
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        brief: ImageBrief,
        keywords: Dict[str, List[str]],
        analysis: Dict[str, Any] | None,
        strategy: Dict[str, Any] | None,
        style_template: StyleTemplate,
        feedback: str | None = None,
    ) -> str:

        # Build the concise base prompt
        base = build_prompt(
            project, brand, product, brief, keywords,
            feedback=feedback,
            style_template=style_template,
        )

        # Enrich with concise analysis insights if available
        enrichment_parts = []

        if analysis:
            # Add only the most impactful analysis insights
            if analysis.get("visual_style"):
                enrichment_parts.append(f"Style: {analysis['visual_style']}")
            if analysis.get("lighting"):
                enrichment_parts.append(f"Lighting: {analysis['lighting']}")
            if analysis.get("composition"):
                enrichment_parts.append(f"Composition: {analysis['composition']}")
            must_avoid = analysis.get("must_avoid", [])
            if must_avoid:
                enrichment_parts.append(f"Avoid: {', '.join(must_avoid[:3])}")

        if strategy:
            # Add key strategy constraints
            if strategy.get("image_type") == "main":
                enrichment_parts.append(
                    "RULES: pure white background, no text, no badges, product fills 85% of frame."
                )
            if strategy.get("background") and strategy.get("image_type") != "main":
                enrichment_parts.append(f"Background: {strategy['background']}")

        # Combine: enrichments first (brief), then the base prompt
        if enrichment_parts:
            enrichment = " | ".join(enrichment_parts)
            return f"{enrichment}\n\n{base}"

        return base
