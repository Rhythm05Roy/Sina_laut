from __future__ import annotations
from typing import List, Dict
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief
from app.schemas.style_template import StyleTemplate
from app.services.slots import slot_default
from app.services.style_instructions import get_style_instructions


def build_prompt(
    project: ProjectSetup,
    brand: BrandCI,
    product: ProductInfo,
    brief: ImageBrief,
    keywords: Dict[str, List[str]],
    feedback: str | None = None,
    style_template: StyleTemplate = StyleTemplate.PLAYFUL,
) -> str:
    """
    Compose a comprehensive prompt for the image generator with multi-modal context
    and style-specific layout instructions.
    """
    key_terms = keywords.get("primary", [])[:5] + keywords.get("secondary", [])[:3]
    usp_text = "; ".join(product.usps) if product.usps else "Highlight core benefits"
    style_hint = f"Style: {brief.style}." if brief.style else ""
    slot_inst = brief.instructions or slot_default(brief.slot_name)
    feedback_hint = f"\nADDITIONAL FEEDBACK TO INCORPORATE: {feedback}" if feedback else ""
    
    # Build emphasis list
    emphasis_text = ", ".join(brief.emphasis) if brief.emphasis else "product quality and benefits"
    
    # Get style-specific layout instructions
    style_layout = get_style_instructions(style_template, brief.slot_name)
    
    # Construct comprehensive prompt
    prompt = f"""CONTEXT: You are an expert e-commerce product image designer. You are given a product image and brand logo as input.
Your task is to create a marketplace-ready product listing image for {project.brand_name} in the {project.product_category} category.

=== CRITICAL REQUIREMENTS ===
1. You MUST incorporate the PROVIDED product image into your design - do NOT generate a different product.
2. Use the EXACT product shown in the input image.
3. If a brand logo is provided, include it as specified in the style instructions.
4. Follow the layout requirements PRECISELY - this is essential for consistency.

=== STYLE TEMPLATE LAYOUT ===
{style_layout}

=== SLOT-SPECIFIC INSTRUCTIONS ===
SLOT TYPE: {brief.slot_name}
ADDITIONAL SLOT INSTRUCTIONS: {slot_inst}
{style_hint}

=== PRODUCT INFORMATION ===
- Brand: {project.brand_name}
- Product Title: {product.title}
- Description: {product.short_description}
- USPs to highlight: {usp_text}
- Key attributes to emphasize: {emphasis_text}

=== CONTENT FOR INFO BADGES ===
Use these for the circular/rectangular info badges:
- Age rating or target audience
- Piece count or quantity (if applicable)
- Key feature 1: {product.usps[0] if product.usps else 'Premium Quality'}
- Key feature 2: {product.usps[1] if len(product.usps) > 1 else 'Great Value'}

=== BRAND GUIDELINES ===
- Primary color: {brand.primary_color} (use for main elements)
- Secondary color: {brand.secondary_color} (use for accents)
- Heading font: {brand.font_heading}
- Body font: {brand.font_body}

=== KEYWORDS TO INCORPORATE ===
Subtly incorporate these keywords: {', '.join(key_terms) if key_terms else 'product quality, premium'}
{feedback_hint}

=== OUTPUT REQUIREMENTS ===
- High resolution (1024x1024 or higher)
- Professional quality suitable for Amazon/Google listings
- Clean, polished final image ready for marketplace use
- Follow the style template layout EXACTLY as specified above
"""
    
    return prompt.strip()
