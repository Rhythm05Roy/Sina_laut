"""
Style-specific layout instructions for image generation.

Each style template has detailed instructions for:
- Logo placement
- Badge style and positioning
- Visual styling (corners, colors)
- Typography
- Overall composition
"""

from typing import Dict
from app.schemas.style_template import StyleTemplate


# Detailed layout instructions for each style template
STYLE_LAYOUTS: Dict[str, Dict[str, str]] = {
    StyleTemplate.PLAYFUL: {
        "name": "Playful",
        "description": "Vibrant, colorful style with rounded shapes and friendly gradients",
        
        "logo_instructions": (
            "LOGO PLACEMENT: "
            "- Place the brand logo where it best balances the composition (top-center by default; shift to a corner if needed to avoid overlap). "
            "- Logo should be prominent and clearly visible if provided. "
            "- If no logo is supplied, leave the area empty (do NOT invent a logo). "
            "- Maintain generous padding around logos (about 5% from top edge)."
        ),
        
        "badge_instructions": (
            "INFO BADGES: "
            "- Create exactly 4 CIRCULAR badges arranged in a horizontal row at the BOTTOM of the image. "
            "- Each badge should have: a solid colored background using brand colors, a small ICON, and brief TEXT (1-3 words). "
            "- Badge content should include: Age rating (e.g., '4+'), Piece count (e.g., '72 pieces'), Key feature icons. "
            "- If you cannot render text cleanly, leave the badge text BLANK rather than inventing or garbling characters. "
            "- Badges should have a slight drop shadow for depth. "
            "- Use alternating brand primary and secondary colors for badges. "
            "- Badge size should be consistent, approximately 80-100px diameter equivalent."
        ),
        
        "product_instructions": (
            "PRODUCT PLACEMENT: "
            "- Center the product image in the middle of the composition. "
            "- Product should occupy about 50-60% of the image height. "
            "- Ensure product is clearly visible and not obscured by other elements. "
            "- Background should be clean white or a soft gradient using brand colors."
        ),
        
        "visual_style": (
            "VISUAL STYLE: "
            "- Use LARGE rounded corners (20-30px radius) on all overlay elements. "
            "- Colors should be VIBRANT and high-contrast. "
            "- Apply subtle gradients to backgrounds and badges. "
            "- Add playful decorative elements if appropriate (sparkles, swooshes). "
            "- Overall feel should be FUN, FRIENDLY, and INVITING."
        ),
        
        "typography": (
            "TYPOGRAPHY: "
            "- Use rounded, bold fonts for headings. "
            "- Text should be large and easily readable. "
            "- Add a catchy tagline or product name below the main product. "
            "- Text colors should contrast well with backgrounds."
        ),
        
        "composition": (
            "COMPOSITION: "
            "- Maintain clear visual hierarchy: Logo > Product > Info badges. "
            "- Use the rule of thirds for placement. "
            "- Ensure adequate white space between elements. "
            "- All elements should feel balanced and professionally arranged."
        ),
    },
    
    StyleTemplate.MODERN: {
        "name": "Modern / Clean",
        "description": "Professional, sleek style with minimal decoration",
        
        "logo_instructions": (
            "LOGO PLACEMENT: "
            "- Place the brand logo in the TOP-LEFT corner. "
            "- Logo should be smaller and more subtle than playful style. "
            "- Use a single-color or monochrome version if available. "
            "- Maintain clean spacing from edges (about 3-4% margin)."
        ),
        
        "badge_instructions": (
            "INFO BADGES: "
            "- Create 3-4 RECTANGULAR badges with small rounded corners (8-12px radius). "
            "- Arrange badges in a horizontal row at the bottom OR vertically on the right side. "
            "- Use muted, professional colors (grays, subtle brand tints). "
            "- Each badge has: minimal icon (line-style), clean text in sans-serif font. "
            "- Badges should have thin borders rather than solid fills. "
            "- Consistent spacing between badges."
        ),
        
        "product_instructions": (
            "PRODUCT PLACEMENT: "
            "- Center the product with generous negative space around it. "
            "- Product should be the clear focal point, occupying 45-55% of image. "
            "- Use pure white background or very subtle gray gradient. "
            "- Consider a subtle shadow or reflection under product."
        ),
        
        "visual_style": (
            "VISUAL STYLE: "
            "- Use MEDIUM rounded corners (8-12px) on overlay elements. "
            "- Color palette should be MUTED and PROFESSIONAL. "
            "- Minimal decorative elements - let the product speak for itself. "
            "- Clean lines and geometric shapes. "
            "- Overall feel should be SOPHISTICATED and TRUSTWORTHY."
        ),
        
        "typography": (
            "TYPOGRAPHY: "
            "- Use clean sans-serif fonts (like Inter, Helvetica). "
            "- Text should be minimal and purposeful. "
            "- Product name in medium weight, features in light weight. "
            "- Maintain strong contrast but avoid pure black on white."
        ),
        
        "composition": (
            "COMPOSITION: "
            "- Emphasize negative space and breathing room. "
            "- Strict alignment and grid-based layout. "
            "- Professional product photography aesthetic. "
            "- All elements precisely positioned."
        ),
    },
    
    StyleTemplate.MINIMAL: {
        "name": "Minimal",
        "description": "Ultra-clean, text-focused style with subtle branding",
        
        "logo_instructions": (
            "LOGO PLACEMENT: "
            "- Place the brand logo in the BOTTOM-RIGHT corner as a subtle watermark. "
            "- Logo should be small and unobtrusive (about 5-8% of image width). "
            "- Use a monochrome or semi-transparent version. "
            "- Logo serves as a signature, not a focal point."
        ),
        
        "badge_instructions": (
            "INFO ELEMENTS: "
            "- NO circular or rectangular badges - use TEXT-ONLY labels. "
            "- Display 2-3 key facts as simple text lines. "
            "- Position text discretely at the bottom or side. "
            "- Use a single accent color sparingly for emphasis. "
            "- Information should be present but not prominent."
        ),
        
        "product_instructions": (
            "PRODUCT PLACEMENT: "
            "- Product is the ABSOLUTE focus - centered with maximum breathing room. "
            "- Product should occupy 40-50% of image with vast white space around. "
            "- Pure white background, no gradients or effects. "
            "- Consider artistic composition with asymmetric placement."
        ),
        
        "visual_style": (
            "VISUAL STYLE: "
            "- NO rounded corners or VERY subtle ones (2-4px). "
            "- Monochromatic or limited to 2 colors maximum. "
            "- No shadows, no gradients, no decorative elements. "
            "- Embrace white space as a design element. "
            "- Overall feel should be ELEGANT and REFINED."
        ),
        
        "typography": (
            "TYPOGRAPHY: "
            "- Use thin, elegant fonts (light weight serif or sans-serif). "
            "- Minimal text - only essential information. "
            "- Small font sizes for supporting text. "
            "- High contrast but subtle presentation."
        ),
        
        "composition": (
            "COMPOSITION: "
            "- Maximum negative space - less is more. "
            "- Product as hero with everything else secondary. "
            "- Asymmetric balance can add interest. "
            "- Gallery or museum-like presentation."
        ),
    },
}


def get_style_instructions(style: StyleTemplate, slot_name: str) -> str:
    """
    Get comprehensive layout instructions for a given style and slot.
    
    Args:
        style: The selected style template
        slot_name: The slot being generated (main_product, key_facts, etc.)
    
    Returns:
        Complete layout instruction string for the prompt
    """
    # For main product, avoid overlay/layout instructions entirely.
    if slot_name == "main_product":
        return ""
    layout = STYLE_LAYOUTS.get(style, STYLE_LAYOUTS[StyleTemplate.PLAYFUL])
    
    # Combine all layout instructions
    instructions = f"""
STYLE TEMPLATE: {layout['name']}
{layout['description']}

{layout['logo_instructions']}

{layout['badge_instructions']}

{layout['product_instructions']}

{layout['visual_style']}

{layout['typography']}

{layout['composition']}
"""
    return instructions.strip()


def get_style_name(style: StyleTemplate) -> str:
    """Get the display name for a style template."""
    return STYLE_LAYOUTS.get(style, {}).get("name", "Playful")
