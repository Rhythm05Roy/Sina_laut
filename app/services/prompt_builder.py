"""
Prompt builder for production-grade marketplace image generation.

Key principles:
- Anti-hallucination: model must ONLY render user-provided text
- Slot-specific context chaining (Image 2+ can reference Image 1)
- Explicit layout instructions per style template
"""

from __future__ import annotations
from typing import List, Dict, Optional
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief
from app.schemas.style_template import StyleTemplate
from app.services.slots import slot_default
from app.services.style_instructions import get_style_instructions


# Global anti-hallucination prefix injected into every prompt
ANTI_HALLUCINATION = """
=== CRITICAL: TEXT RENDERING RULES ===
You are generating a product image for an e-commerce marketplace.
- DO NOT generate random, garbled, or hallucinated text.
- ONLY render the EXACT text strings provided in this prompt.
- If no text is specified for an element, leave that element WITHOUT text.
- Every word in the output image must come directly from this prompt.
- Misspelled or gibberish text is UNACCEPTABLE — double-check every character.
""".strip()


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
    Compose a comprehensive prompt for the image generator.

    The prompt includes:
    - Anti-hallucination guardrails
    - Slot-specific instructions (from slots.py)
    - Style-specific layout (from style_instructions.py)
    - Product info and brand guidelines
    - User-provided emphasis text (rendered verbatim)
    """
    usp_text = "; ".join(product.usps) if product.usps else ""
    style_hint = f"Visual style: {brief.style}." if brief.style else ""
    slot_inst = brief.instructions or slot_default(brief.slot_name)
    feedback_hint = f"\nADDITIONAL REFINEMENT FEEDBACK: {feedback}" if feedback else ""

    # Build emphasis / user-provided text list
    emphasis_items = brief.emphasis if brief.emphasis else []
    emphasis_block = ""
    if emphasis_items:
        lines = [f'  {i+1}. "{item}"' for i, item in enumerate(emphasis_items) if item.strip()]
        if lines:
            emphasis_block = "USER-PROVIDED TEXT TO RENDER VERBATIM:\n" + "\n".join(lines)

    # Get style-specific layout instructions
    style_layout = get_style_instructions(style_template, brief.slot_name)

    # Determine slot-specific sections
    slot_specific = ""
    if brief.slot_name == "main_product":
        slot_specific = (
            "THIS IS A BACKGROUND-REMOVAL-ONLY TASK.\n"
            "Do NOT add ANY elements. Just clean the background to white and center the product."
        )
    elif brief.slot_name == "key_facts":
        slot_specific = (
            "RENDER THESE EXACT KEY FACTS ON THE INFO CARDS:\n"
            + "\n".join(f'  Card {i+1}: "{e}"' for i, e in enumerate(emphasis_items) if e.strip())
            if emphasis_items else "No key facts provided."
        )
    elif brief.slot_name == "usps":
        usp_lines = [f'  USP {i+1}: "{u}"' for i, u in enumerate(product.usps) if u] if product.usps else []
        if emphasis_items:
            usp_lines = [f'  USP {i+1}: "{e}"' for i, e in enumerate(emphasis_items) if e.strip()]
        slot_specific = (
            "RENDER THESE EXACT USP TEXTS ON THE CALLOUT BOXES:\n"
            + "\n".join(usp_lines)
            if usp_lines else "Use the product USPs."
        )
    elif brief.slot_name == "comparison":
        slot_specific = (
            "USE THESE EXACT TEXTS FOR THE COMPARISON:\n"
            + "\n".join(f'  • "{e}"' for e in emphasis_items if e.strip())
            if emphasis_items else "Use generic comparison."
        )
    elif brief.slot_name == "cross_selling":
        slot_specific = (
            "USE THESE EXACT PRODUCT NAMES FOR THE GRID:\n"
            + "\n".join(f'  Slot {i+1}: "{e}"' for i, e in enumerate(emphasis_items) if e.strip())
            if emphasis_items else "Use generic product placeholders."
        )
    elif brief.slot_name == "closing":
        headline = emphasis_items[0] if emphasis_items and emphasis_items[0].strip() else ""
        direction = brief.style or "Emotional"
        slot_specific = (
            f"DIRECTION: {direction}\n"
            f'HEADLINE TO RENDER: "{headline}"' if headline else
            f"DIRECTION: {direction}\nNo headline — create a purely visual composition."
        )

    prompt = f"""{ANTI_HALLUCINATION}

=== TASK ===
{slot_inst}

=== SLOT TYPE ===
{brief.slot_name}
{style_hint}

{slot_specific}

=== PRODUCT INFORMATION ===
- Brand: {project.brand_name}
- Product: {product.title}
- Description: {product.short_description}
{f'- USPs: {usp_text}' if usp_text else ''}

=== BRAND GUIDELINES ===
- Primary color: {brand.primary_color}
- Secondary color: {brand.secondary_color}
- Heading font: {brand.font_heading}
- Body font: {brand.font_body}

{emphasis_block}

=== STYLE LAYOUT ===
{style_layout}

=== OUTPUT REQUIREMENTS ===
- Resolution: 1024×1024 or higher
- Professional quality suitable for Amazon / Google marketplace
- Clean, polished, production-ready
{feedback_hint}
"""
    return prompt.strip()
