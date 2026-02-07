from __future__ import annotations
from typing import List, Dict
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief


def build_prompt(
    project: ProjectSetup,
    brand: BrandCI,
    product: ProductInfo,
    brief: ImageBrief,
    keywords: Dict[str, List[str]],
) -> str:
    """Compose a human readable prompt for the image generator."""
    primary_marketplace = project.target_marketplaces[0].value if project.target_marketplaces else None
    key_terms = keywords.get(primary_marketplace, []) if primary_marketplace else []
    usp_text = "; ".join(product.usps) if product.usps else "Highlight core benefits"
    style_hint = f"Style: {brief.style}." if brief.style else ""

    return (
        f"Create a product marketing image for {project.brand_name} in the {project.product_category} category. "
        f"Slot: {brief.slot_name}. {brief.instructions}. {style_hint} "
        f"Product title: {product.title}. USP: {usp_text}. "
        f"Use primary color {brand.primary_color} and secondary color {brand.secondary_color} accents. "
        f"Fonts: heading {brand.font_heading}, body {brand.font_body}. "
        f"Emphasize attributes: {', '.join(brief.emphasis) if brief.emphasis else 'product quality and benefits'}. "
        f"Include keywords subtly: {', '.join(key_terms[:6])}. "
        "Output should be high resolution, marketplace compliant, no additional text unless specified."
    )
