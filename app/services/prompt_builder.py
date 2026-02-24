"""
Prompt builder for production-grade marketplace image generation.

Produces CONCISE prompts optimized for Gemini's image generation model.
Gemini image gen works best with focused, descriptive prompts (~300-600 chars),
not lengthy instruction manuals.
"""

from __future__ import annotations
from typing import List, Dict, Optional
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.schemas.image import ImageBrief
from app.schemas.style_template import StyleTemplate
from app.services.slots import slot_default

# Helper to join keyword-driven statements deterministically
def _benefit_lines(keywords: List[str], count: int, prefix: str) -> str:
    lines = []
    for kw in keywords[:count]:
        lines.append(f"{prefix} {kw}".strip())
    return "; ".join(lines)


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
    Compose a concise, effective prompt for Gemini image generation.

    The prompt is focused and descriptive rather than instructional,
    because Gemini image gen responds better to descriptions of what
    the image should look like rather than lists of rules.
    """
    slot = brief.slot_name

    # --- Slot-specific prompt ---
    if slot == "main_product":
        prompt = _main_product_prompt(project, brand, product, brief)
    elif slot == "key_facts":
        prompt = _key_facts_prompt(project, brand, product, brief, keywords)
    elif slot == "lifestyle":
        prompt = _lifestyle_prompt(project, brand, product, brief, keywords)
    elif slot == "usps":
        prompt = _usps_prompt(project, brand, product, brief, keywords)
    elif slot == "comparison":
        prompt = _comparison_prompt(project, brand, product, brief, keywords)
    elif slot == "cross_selling":
        prompt = _cross_selling_prompt(project, brand, product, brief)
    elif slot == "closing":
        prompt = _closing_prompt(project, brand, product, brief, keywords)
    else:
        prompt = _generic_prompt(project, brand, product, brief)

    # Append feedback if refining
    if feedback:
        prompt += f"\n\nREFINEMENT: {feedback}"

    return prompt.strip()


def _main_product_prompt(project, brand, product, brief) -> str:
    """Main product image: clean white background, product only."""
    return (
        f"Professional e-commerce product photography of {product.title}. "
        f"Pure white background (#FFFFFF). Product centered, filling 85% of frame. "
        f"Clean, sharp edges. Soft natural shadow beneath product. "
        f"Shot with 85mm lens, f/11, even studio lighting. "
        f"No added text, no added logos, no badges, no decorations. Preserve all original on-product branding/labels/text exactly as in the photo. "
        f"Amazon marketplace compliant hero image. Ultra-sharp detail, production-ready."
    )


def _key_facts_prompt(project, brand, product, brief, keywords) -> str:
    """Key facts: product with info cards layout."""
    facts = brief.emphasis[:4] if brief.emphasis else product.usps[:4]
    visual_kws = keywords.get("clean_visual") or keywords.get("primary", [])
    # Build four short benefit lines (max 3 words each), drop intent-y terms
    benefit_lines = []
    for kw in visual_kws:
        if any(t in kw for t in ["buy", "deal", "price", "offer", "cheap"]):
            continue
        words = kw.split()[:3]
        phrase = " ".join(words).strip()
        if phrase and phrase not in benefit_lines:
            benefit_lines.append(phrase)
        if len(benefit_lines) >= 4:
            break
    if not benefit_lines:
        benefit_lines = [f for f in facts if f][:4]
    facts_text = "; ".join(benefit_lines) if benefit_lines else "key product features"

    return (
        f"Professional product infographic for {product.title} by {project.brand_name}. "
        f"Clean marketing layout on a professional background. "
        f"Product image prominently displayed. "
        f"{facts_text}. "
        f"Brand colors: {brand.primary_color} primary, {brand.secondary_color} secondary. "
        f"Clean sans-serif typography. Professional e-commerce infographic quality. "
        f"Render text exactly as provided, do not invent text."
    )


def _lifestyle_prompt(project, brand, product, brief, keywords) -> str:
    """Lifestyle: product in real-world scenario."""
    scenario = brief.instructions or "being used naturally in an appropriate real-world setting"
    secondary = keywords.get("clean_visual") or keywords.get("secondary", [])
    claims = []
    for kw in secondary:
        if any(t in kw for t in ["buy", "deal", "price", "offer", "cheap"]):
            continue
        phrase = " ".join(kw.split()[:3]).strip()
        if phrase and phrase not in claims:
            claims.append(phrase)
        if len(claims) >= 3:
            break
    claims_text = "; ".join(claims) if claims else ""

    return (
        f"Professional lifestyle photography of {product.title}. "
        f"{scenario}. "
        f"{f'Contextual claims: {claims_text}. ' if claims_text else ''}"
        f"Product is the hero of the scene, clearly visible and recognizable. "
        f"Professional studio-quality warm natural lighting, shallow depth of field. "
        f"High-end commercial photography aesthetic. Realistic, aspirational. "
        f"No text overlays, no logos, no artificial elements."
    )


def _usps_prompt(project, brand, product, brief, keywords) -> str:
    """USP highlight: product with callouts around it."""
    primary = keywords.get("clean_visual") or keywords.get("primary", [])
    usps = primary[:3] if primary else (brief.emphasis[:3] if brief.emphasis else product.usps[:3])
    usps_text = "; ".join(u for u in usps if u) if usps else "unique features"

    return (
        f"Professional USP highlight infographic for {product.title} by {project.brand_name}. "
        f"Product centered in the composition. "
        f"3 clean callout texts arranged around the product with these exact USPs: {usps_text}. "
        f"Text-only callouts in clean sans-serif font; no icons unless provided. "
        f"Brand colors: {brand.primary_color} primary, {brand.secondary_color} secondary. "
        f"Clean gradient background. Professional marketing layout. "
        f"Only render the exact text provided."
    )


def _comparison_prompt(project, brand, product, brief, keywords) -> str:
    """Comparison: split layout with advantages vs limitations."""
    primary = keywords.get("clean_visual") or keywords.get("primary", [])
    secondary = keywords.get("clean_visual") or keywords.get("secondary", [])

    adv = []
    for kw in primary:
        if any(t in kw for t in ["buy", "deal", "price", "offer", "cheap"]):
            continue
        adv.append(" ".join(kw.split()[:3]))
        if len(adv) >= 2:
            break
    if not adv:
        adv = ["Better build", "Trusted brand"]

    lim = []
    for kw in secondary:
        if any(t in kw for t in ["buy", "deal", "price", "offer", "cheap"]):
            continue
        lim.append(" ".join(kw.split()[:3]))
        if len(lim) >= 2:
            break
    if not lim:
        lim = ["Generic alternative", "Lower quality"]

    adv_text = ", ".join(f'"{a}"' for a in adv)
    lim_text = ", ".join(f'"{l}"' for l in lim)

    return (
        f"Professional comparison infographic for {product.title}. "
        f"Split layout: LEFT side 'Our Product' with green checkmarks showing advantages: {adv_text}. "
        f"RIGHT side 'Others' with red X marks showing limitations: {lim_text}. "
        f"Clean white background. Professional typography. "
        f"Brand colors: {brand.primary_color}. "
        f"Easy to read at a glance. Only render the exact text provided."
    )


def _cross_selling_prompt(project, brand, product, brief) -> str:
    """Cross-selling: grid of related products."""
    names = brief.emphasis or []
    names_text = ", ".join(f'"{n}"' for n in names[:6]) if names else "related products"

    return (
        f"Professional cross-selling product showcase for {product.title} by {project.brand_name}. "
        f"Main product featured prominently at top. "
        f"Below: a clean grid layout of related product cards: {names_text}. "
        f"Each card has a product placeholder image and the exact product name label. "
        f"Call to action 'Discover More' at bottom in brand color {brand.primary_color}. "
        f"Clean white background. Professional e-commerce layout."
    )


def _closing_prompt(project, brand, product, brief, keywords) -> str:
    """Closing: emotional/inspirational final image."""
    headline = brief.emphasis[0] if brief.emphasis and brief.emphasis[0].strip() else None
    direction = brief.style or "Emotional"
    primary = keywords.get("primary", [])
    secondary = keywords.get("secondary", [])
    keyword_line = ""
    if primary or secondary:
        keyword_line = f" Conversion line with: {primary[0] if primary else ''} {secondary[0] if secondary else ''}."

    base = (
        f"Premium closing brand image for {product.title} by {project.brand_name}. "
        f"{direction} direction. "
        f"Product displayed beautifully with dramatic, atmospheric lighting. "
        f"Rich background with brand colors {brand.primary_color}/{brand.secondary_color}. "
        f"Brand logo prominently displayed. "
    )
    if headline:
        base += f'Large elegant headline text: "{headline}". '
    else:
        base += "No text — purely visual composition. "
    base += "Premium brand campaign quality. Final impression image."
    if keyword_line:
        base += keyword_line
    return base


def _generic_prompt(project, brand, product, brief) -> str:
    """Fallback for unknown slot types."""
    return (
        f"Professional marketplace product image for {product.title} by {project.brand_name}. "
        f"{brief.instructions or 'Clean, production-ready marketing image.'}. "
        f"Brand colors: {brand.primary_color}/{brand.secondary_color}. "
        f"Professional quality suitable for Amazon/Google marketplace."
    )
