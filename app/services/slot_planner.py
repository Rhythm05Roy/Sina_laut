from __future__ import annotations

from typing import Iterable

from app.core.config import Settings
from app.schemas.brand import BrandCI
from app.schemas.image import ImageBrief
from app.schemas.product import ProductInfo
from app.schemas.project import ProjectSetup
from app.schemas.style_template import StyleTemplate
from app.services.gemini_market_planner import GeminiMarketPlanner
from app.services.pipeline_models import (
    CompositionPlan,
    KeywordPlan,
    ProductAnalysis,
    SlotCopyPlan,
    SlotPlan,
    SlotVisualPlan,
)


INTENT_TERMS = {"buy", "best", "price", "deal", "offer", "cheap", "discount"}


class SlotPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market_planner = GeminiMarketPlanner(settings)

    async def plan_slot(
        self,
        *,
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        brief: ImageBrief,
        style_template: StyleTemplate,
        analysis: ProductAnalysis,
        keyword_plan: KeywordPlan,
        primary_image: str | None = None,
        feedback: str | None = None,
    ) -> SlotPlan:
        marketplace = project.target_marketplaces[0] if project.target_marketplaces else "amazon"
        slot_hints = await self.market_planner.plan_slot(
            project=project,
            product=product,
            brief=brief,
            analysis=analysis,
            keyword_plan=keyword_plan,
            marketplace=marketplace,
        )
        copy_plan = self._build_copy_plan(brief, product, keyword_plan, slot_hints)
        visual_plan = self._build_visual_plan(brief, style_template, analysis, copy_plan)
        generation_prompt = self._build_draft_prompt(
            project=project,
            brand=brand,
            product=product,
            brief=brief,
            analysis=analysis,
            copy_plan=copy_plan,
            visual_plan=visual_plan,
            feedback=feedback,
        )
        return SlotPlan(
            slot_name=brief.slot_name,
            analysis=analysis,
            keyword_plan=keyword_plan,
            copy_plan=copy_plan,
            visual_plan=visual_plan,
            generation_prompt=generation_prompt,
        )

    def _clean_items(self, values: Iterable[str], limit: int) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = " ".join(str(value).strip().split())
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(text[:60])
            if len(cleaned) >= limit:
                break
        return cleaned

    def _keyword_text(self, keyword_plan: KeywordPlan, limit: int) -> list[str]:
        if not keyword_plan.available:
            return []
        filtered = [
            kw for kw in keyword_plan.clean_visual
            if not any(term in kw.lower() for term in INTENT_TERMS)
        ]
        return self._clean_items(filtered, limit)

    def _build_copy_plan(
        self,
        brief: ImageBrief,
        product: ProductInfo,
        keyword_plan: KeywordPlan,
        slot_hints: dict[str, object] | None = None,
    ) -> SlotCopyPlan:
        slot_name = brief.slot_name
        slot_hints = slot_hints or {}
        explicit = self._clean_items(brief.emphasis, 8)
        keyword_text = self._keyword_text(keyword_plan, 8)

        if slot_name == "main_product":
            return SlotCopyPlan(overlay_enabled=False, notes=["main image does not allow overlays"])

        if slot_name == "key_facts":
            hinted = self._clean_items(slot_hints.get("callouts", []), 4)
            callouts = hinted[:4] or explicit[:4] or keyword_text[:4]
            return SlotCopyPlan(
                overlay_enabled=bool(callouts),
                callouts=callouts,
                notes=["render as exact fact cards", "skip overlay if no explicit or keyword text"],
            )

        if slot_name == "lifestyle":
            hinted = self._clean_items(slot_hints.get("callouts", []), 3)
            callouts = hinted[:3] or explicit[:3] or keyword_text[:3]
            return SlotCopyPlan(
                overlay_enabled=bool(callouts),
                scenario=self._clean_items([slot_hints.get("scenario", "")], 1)[0] if slot_hints.get("scenario") else None,
                callouts=callouts,
                notes=["keep claims minimal and contextual", "use visual-only output if no overlay text available"],
            )

        if slot_name == "usps":
            hinted_headline = self._clean_items([slot_hints.get("headline", "")], 1)[0] if slot_hints.get("headline") else None
            hinted_callouts = self._clean_items(slot_hints.get("callouts", []), 3)
            if len(explicit) == 1 and not hinted_callouts:
                return SlotCopyPlan(
                    overlay_enabled=True,
                    headline=hinted_headline or explicit[0],
                    notes=["single focused headline"],
                )
            callouts = hinted_callouts[:3] or explicit[:3] or keyword_text[:3]
            return SlotCopyPlan(
                overlay_enabled=bool(callouts),
                callouts=callouts,
                headline=hinted_headline or (explicit[0] if explicit and len(explicit) > 1 else None),
                notes=["use structured USP callouts", "no free-floating badges"],
            )

        if slot_name == "comparison":
            left = self._clean_items(slot_hints.get("comparison_left", []), 3) or [item[4:] for item in explicit if item.startswith("ADV:")]
            right = self._clean_items(slot_hints.get("comparison_right", []), 3) or [item[4:] for item in explicit if item.startswith("LIM:")]
            if not left and keyword_text:
                left = keyword_text[:3]
            if not right and keyword_plan.available:
                right = [
                    "generic alternative",
                    "unclear durability",
                    "less refined finish",
                ][: max(0, min(3, len(left) or 2))]
            return SlotCopyPlan(
                overlay_enabled=bool(left or right),
                comparison_left=self._clean_items(left, 3),
                comparison_right=self._clean_items(right, 3),
                notes=["fixed two-column comparison"],
            )

        if slot_name == "cross_selling":
            labels = self._clean_items(slot_hints.get("product_labels", []), 6) or explicit[:6]
            return SlotCopyPlan(
                overlay_enabled=bool(labels),
                product_labels=labels,
                notes=["exact product labels only"],
            )

        if slot_name == "closing":
            closing_line = self._clean_items([slot_hints.get("closing_line", "")], 1)[0] if slot_hints.get("closing_line") else (explicit[0] if explicit else None)
            if not closing_line and keyword_plan.available:
                keyword = keyword_plan.primary[0] if keyword_plan.primary else ""
                if keyword:
                    closing_line = f"{product.title} | {keyword.title()}"
            return SlotCopyPlan(
                overlay_enabled=bool(closing_line),
                headline=self._clean_items([slot_hints.get("headline", "")], 1)[0] if slot_hints.get("headline") else None,
                closing_line=closing_line,
                notes=["single controlled closing line only"],
            )

        return SlotCopyPlan(overlay_enabled=False)

    def _background_for_style(self, style_template: StyleTemplate, slot_name: str, analysis: ProductAnalysis) -> str:
        if slot_name == "main_product":
            return "pure white seamless background"
        if analysis.background:
            return analysis.background
        if style_template == StyleTemplate.MINIMAL:
            return "soft neutral backdrop"
        if style_template == StyleTemplate.MODERN:
            return "clean commercial gradient background"
        return "polished brand-tinted background"

    def _build_visual_plan(
        self,
        brief: ImageBrief,
        style_template: StyleTemplate,
        analysis: ProductAnalysis,
        copy_plan: SlotCopyPlan,
    ) -> SlotVisualPlan:
        slot_name = brief.slot_name
        image_type = {
            "main_product": "main",
            "lifestyle": "lifestyle",
        }.get(slot_name, "infographic")

        if slot_name == "key_facts":
            composition_plan = CompositionPlan(
                layout="product-left cards-right",
                reserved_regions=["right cards", "top logo"],
                max_text_items=4,
                card_style="rounded rectangles",
                text_alignment="left",
            )
        elif slot_name == "comparison":
            composition_plan = CompositionPlan(
                layout="split comparison board",
                reserved_regions=["top header", "left column", "right column"],
                max_text_items=6,
                card_style="clean rows",
                text_alignment="left",
            )
        elif slot_name == "cross_selling":
            composition_plan = CompositionPlan(
                layout="hero with 3x2 grid",
                reserved_regions=["top hero", "bottom product grid"],
                max_text_items=6,
                card_style="product labels",
                text_alignment="center",
            )
        elif slot_name == "closing":
            composition_plan = CompositionPlan(
                layout="hero with bottom copy strip",
                reserved_regions=["bottom strip"],
                max_text_items=1,
                card_style="headline strip",
                text_alignment="center",
            )
        elif slot_name == "lifestyle":
            composition_plan = CompositionPlan(
                layout="hero lifestyle with optional claim strip",
                reserved_regions=["bottom left copy"] if copy_plan.overlay_enabled else [],
                max_text_items=3,
                card_style="subtle text strip",
                text_alignment="left",
            )
        elif slot_name == "usps":
            composition_plan = CompositionPlan(
                layout="center product with side callouts",
                reserved_regions=["right callout stack", "top header"],
                max_text_items=4,
                card_style="clean callout bars",
                text_alignment="left",
            )
        else:
            composition_plan = CompositionPlan(layout="clean hero", reserved_regions=[], max_text_items=0)

        must_avoid = list(analysis.must_avoid)
        if copy_plan.overlay_enabled:
            must_avoid.extend(["rendered text", "AI-generated badges", "icons inside base image"])
        background = self._background_for_style(style_template, slot_name, analysis)
        composition = analysis.composition or composition_plan.layout
        text_allowed = slot_name != "main_product" and copy_plan.overlay_enabled
        logo_allowed = slot_name != "main_product"
        return SlotVisualPlan(
            slot_name=slot_name,
            image_type=image_type,
            background=background,
            composition=composition,
            text_allowed=text_allowed,
            logo_allowed=logo_allowed,
            composition_plan=composition_plan,
            must_avoid=self._clean_items(must_avoid, 8),
        )

    def _build_draft_prompt(
        self,
        *,
        project: ProjectSetup,
        brand: BrandCI,
        product: ProductInfo,
        brief: ImageBrief,
        analysis: ProductAnalysis,
        copy_plan: SlotCopyPlan,
        visual_plan: SlotVisualPlan,
        feedback: str | None,
    ) -> str:
        prompt_parts = [
            f"Professional e-commerce image of {product.title} for {project.brand_name}.",
            f"Background: {visual_plan.background}.",
            f"Composition: {visual_plan.composition}.",
        ]
        if analysis.lighting:
            prompt_parts.append(f"Lighting: {analysis.lighting}.")
        if analysis.visual_style:
            prompt_parts.append(f"Visual style: {analysis.visual_style}.")
        palette_hint = self._palette_hint(brand)
        if palette_hint:
            prompt_parts.append(palette_hint)

        prompt_parts.extend(self._slot_prompt_parts(brief, copy_plan, visual_plan))

        if analysis.must_avoid:
            prompt_parts.append("Avoid " + ", ".join(self._clean_items(analysis.must_avoid, 5)) + ".")
        if feedback:
            prompt_parts.append(f"Refinement: {feedback}.")
        return " ".join(part.strip() for part in prompt_parts if part and part.strip())

    def _palette_hint(self, brand: BrandCI) -> str:
        parts: list[str] = []
        if brand.primary_color:
            parts.append(f"primary {brand.primary_color}")
        if brand.secondary_color:
            parts.append(f"secondary {brand.secondary_color}")
        if not parts:
            return ""
        return "Use subtle brand palette accents: " + ", ".join(parts) + "."

    def _slot_prompt_parts(
        self,
        brief: ImageBrief,
        copy_plan: SlotCopyPlan,
        visual_plan: SlotVisualPlan,
    ) -> list[str]:
        slot_name = brief.slot_name
        if slot_name == "main_product":
            return [
                "Use the provided source photo as the exact product reference and only clean the scene around it.",
                "Preserve the exact product identity and all on-product printed branding.",
                "Pure white seamless background, product centered, clean edges, soft natural contact shadow.",
                "No added text, no logo overlays, no props, no badges, no decorative graphics.",
            ]

        parts = [
            "Do not render any text, letters, labels, logos, icons, badges, or UI elements into the image itself.",
        ]
        if visual_plan.composition_plan.reserved_regions:
            parts.append(
                "Leave clean negative space for overlay composition in these regions: "
                + ", ".join(visual_plan.composition_plan.reserved_regions)
                + "."
            )

        if slot_name == "key_facts":
            parts.extend([
                "Generate a clean premium infographic background only, with no product object included.",
                "Left side stays open for the exact product image to be composited later.",
                "Right side stays clean and balanced for structured fact cards.",
                "Commercial studio look, polished and marketplace-ready.",
            ])
        elif slot_name == "lifestyle":
            scenario = copy_plan.scenario or (brief.instructions.strip() if brief.instructions else "Real-world aspirational usage scene.")
            parts.extend([
                scenario,
                "Generate the believable lifestyle environment only, leaving clear foreground space for the exact product to be composited later.",
                "Natural commercial photography, believable environment, no stock-photo clutter.",
            ])
        elif slot_name == "usps":
            parts.extend([
                "Generate a clean premium background only, with no product object included.",
                "Leave the left side open for the exact product image and the right side for structured callouts.",
                "Balanced premium composition, no floating graphic elements in the base image.",
            ])
            if copy_plan.headline:
                parts.append(f"Visual theme should support this headline: {copy_plan.headline}.")
        elif slot_name == "comparison":
            parts.extend([
                "Generate a clean neutral backdrop only, with no product object included.",
                "Leave space for a supporting hero product panel and a two-column comparison board.",
            ])
        elif slot_name == "cross_selling":
            parts.extend([
                "Generate a clean brand-consistent background only, with no product objects included.",
                "Keep the top-left hero region and lower grid region clean for later composition.",
            ])
        elif slot_name == "closing":
            parts.extend([
                "Generate a premium campaign background only, with no product object included.",
                "Keep the center hero region and lower strip clean for later composition.",
                "Strong campaign finish, realistic materials, controlled atmosphere.",
            ])
            if copy_plan.headline:
                parts.append(f"Visual direction should support this headline: {copy_plan.headline}.")
            if copy_plan.closing_line:
                parts.append(f"Visual tone should support this closing line: {copy_plan.closing_line}.")

        return parts
