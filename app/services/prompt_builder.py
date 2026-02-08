from __future__ import annotations
from typing import List, Dict
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief
from app.services.slots import slot_default


def build_prompt(
    project: ProjectSetup,
    brand: BrandCI,
    product: ProductInfo,
    brief: ImageBrief,
    keywords: Dict[str, List[str]],
    feedback: str | None = None,
) -> str:
    """Compose a deterministic prompt for the image generator."""
    key_terms = keywords.get("primary", [])[:5] + keywords.get("secondary", [])[:3]
    usp_text = "; ".join(product.usps) if product.usps else "Highlight core benefits"
    style_hint = f"Style: {brief.style}." if brief.style else ""
    slot_inst = brief.instructions or slot_default(brief.slot_name)
    feedback_hint = f"Refine per feedback: {feedback}." if feedback else ""

    return (
        f"Create a marketplace-ready product image for {project.brand_name} in the {project.product_category} category. "
        f"Slot: {brief.slot_name}. {slot_inst} {style_hint} "
        f"Product title: {product.title}. USP: {usp_text}. "
        f"Use primary color {brand.primary_color} and secondary color {brand.secondary_color} accents. "
        f"Fonts: heading {brand.font_heading}, body {brand.font_body}. "
        f"Emphasize attributes: {', '.join(brief.emphasis) if brief.emphasis else 'product quality and benefits'}. "
        f"Include keywords subtly: {', '.join(key_terms)}. "
        f"{feedback_hint} "
        "Output must be high resolution, compliant with Amazon/Google listing policies, minimal extra text unless specified."
    )
