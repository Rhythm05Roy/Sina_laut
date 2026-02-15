"""
Production-grade slot templates for marketplace image generation.

Each slot has a carefully crafted prompt that:
- Prevents text hallucination (uses EXACT user-provided text only)
- Specifies precise layout composition
- Includes anti-hallucination guardrails
"""

from typing import Dict, List, Optional


SLOT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "main_product": {
        "title": "Main Image",
        "instructions": (
            "TASK: Clean up the provided product image for marketplace listing. "
            "DO ONLY THE FOLLOWING: "
            "1. Remove the existing background and replace with PURE WHITE (#FFFFFF). "
            "2. Center the product so it fills approximately 85% of the frame. "
            "3. Ensure the product edges are clean and sharp. "
            "4. Maintain the original product appearance exactly as-is. "
            "\n"
            "DO NOT DO ANY OF THE FOLLOWING: "
            "- Do NOT add any text, titles, labels, or watermarks. "
            "- Do NOT add any logos or brand elements. "
            "- Do NOT add badges, icons, or decorative graphics. "
            "- Do NOT add borders, frames, or shadows. "
            "- Do NOT modify the product itself in any way. "
            "- Do NOT generate a different product — use ONLY the provided image. "
            "\n"
            "OUTPUT: A clean product photo on pure white background, nothing else."
        ),
    },

    "key_facts": {
        "title": "Key Facts",
        "instructions": (
            "TASK: Create a professional product infographic with EXACTLY 4 key fact callouts. "
            "\n"
            "LAYOUT REQUIREMENTS: "
            "1. BACKGROUND: Clean, professional background using the specified style. "
            "2. PRODUCT: Place the product image prominently on the LEFT side (50-60% width). "
            "3. KEY FACTS: Place EXACTLY 4 rectangular info cards on the RIGHT side, stacked vertically. "
            "   - Each card has a small icon and the EXACT text provided by the user. "
            "   - Cards should have rounded corners, subtle shadow, and use brand colors. "
            "4. BRAND LOGO: Place at the specified position (top, bottom, etc.). "
            "\n"
            "CRITICAL TEXT RULES: "
            "- Render ONLY the exact key fact text strings provided below. "
            "- DO NOT invent, paraphrase, or hallucinate any text. "
            "- If a key fact is empty, skip it — do not make up content. "
            "- Text must be LEGIBLE: use clean sans-serif font, minimum 18pt equivalent. "
            "\n"
            "QUALITY: Professional infographic quality suitable for Amazon/Google marketplace listing."
        ),
    },

    "lifestyle": {
        "title": "Lifestyle",
        "instructions": (
            "TASK: Create a premium lifestyle photograph showing the product in real-world use. "
            "\n"
            "COMPOSITION REQUIREMENTS: "
            "1. SCENE: A realistic, aspirational setting matching the scenario description. "
            "2. PRODUCT VISIBILITY: The product must be clearly visible and recognizable — "
            "   it should be the hero of the scene, not a background element. "
            "3. LIGHTING: Professional studio-quality lighting — warm, natural, inviting. "
            "   Use golden-hour style warmth for indoor scenes, bright natural light for outdoors. "
            "4. DEPTH OF FIELD: Shallow depth of field with product in sharp focus. "
            "5. COLOR GRADING: Professional color grading — warm tones, high dynamic range. "
            "\n"
            "DO NOT: "
            "- Do NOT add any text overlays, labels, or captions to the image. "
            "- Do NOT add logos or brand elements. "
            "- Do NOT make the scene look artificial or stock-photo generic. "
            "\n"
            "QUALITY: Professional advertising photography quality — this should look like a "
            "high-budget brand campaign shot, not a basic product photo."
        ),
    },

    "usps": {
        "title": "USP Highlight",
        "instructions": (
            "TASK: Create a professional USP (Unique Selling Points) highlight image. "
            "\n"
            "LAYOUT REQUIREMENTS: "
            "1. PRODUCT: Place the product image CENTERED in the composition. "
            "2. USP CALLOUTS: Arrange 3-4 USP callout boxes AROUND the product: "
            "   - Each callout is a rounded rectangle with: "
            "     • A small relevant ICON (e.g., shield for quality, clock for speed) "
            "     • The EXACT USP text provided by the user (one line, bold) "
            "   - Connect each callout to the product with a thin line or arrow. "
            "   - Use brand primary color for callout backgrounds, white text. "
            "3. BRAND LOGO: Small, in the top-left or top-right corner. "
            "4. BACKGROUND: Clean gradient or solid using brand secondary color (light). "
            "\n"
            "CRITICAL TEXT RULES: "
            "- Render ONLY the exact USP text strings provided below. "
            "- DO NOT invent, paraphrase, or hallucinate any text. "
            "- Each USP text must be rendered in a CLEAR, READABLE font. "
            "- Minimum font size equivalent to 20pt for USP labels. "
            "\n"
            "QUALITY: Premium marketing infographic — clean, scannable, professional."
        ),
    },

    "comparison": {
        "title": "Comparison",
        "instructions": (
            "TASK: Create a professional product comparison image (Us vs Others). "
            "\n"
            "LAYOUT REQUIREMENTS: "
            "1. SPLIT LAYOUT: Divide the image into TWO vertical halves: "
            "   - LEFT HALF (Our Product — Advantages): "
            "     • Header: '✓ Our Product' in green/brand color "
            "     • List 3 advantage items with GREEN checkmarks "
            "     • Clean, professional card-style rows "
            "   - RIGHT HALF (Other Products — Limitations): "
            "     • Header: '✗ Others' in red/gray "
            "     • List 3 limitation items with RED X marks "
            "     • Same card-style rows for visual consistency "
            "2. PRODUCT: Small product image at the top center or left-center. "
            "3. BRAND LOGO: Top corner, small. "
            "4. BACKGROUND: Clean white or very light gray. "
            "\n"
            "CRITICAL TEXT RULES: "
            "- Render ONLY the exact advantage and limitation texts provided below. "
            "- DO NOT invent, paraphrase, or hallucinate any text. "
            "- Use clear, sans-serif font. Green for advantages, red for limitations. "
            "\n"
            "QUALITY: Clean comparison infographic — easy to read at a glance."
        ),
    },

    "cross_selling": {
        "title": "Cross-Selling",
        "instructions": (
            "TASK: Create a cross-selling product showcase image. "
            "\n"
            "LAYOUT REQUIREMENTS: "
            "1. HERO PRODUCT: Place the main product LARGER at the top-center (30-40% of height). "
            "2. RELATED PRODUCTS GRID: Below the hero, create a 3×2 grid of 6 product slots: "
            "   - Each slot is a card with rounded corners and subtle border. "
            "   - Each card shows: a product placeholder image area + product label below. "
            "   - Use the EXACT product names provided by the user as labels. "
            "3. CALL TO ACTION: Include text 'Discover More' or 'Complete Your Collection' "
            "   in brand primary color at the bottom. "
            "4. BRAND LOGO: Top-left, small. "
            "5. BACKGROUND: Clean white with subtle grid lines or soft gradient. "
            "\n"
            "CRITICAL TEXT RULES: "
            "- Use ONLY the exact product names provided below for the grid labels. "
            "- DO NOT invent product names or descriptions. "
            "- Text must be legible and professionally typeset. "
            "\n"
            "QUALITY: Professional e-commerce cross-sell layout — clean, organized, inviting."
        ),
    },

    "closing": {
        "title": "Closing",
        "instructions": (
            "TASK: Create a powerful closing / emotional image for the product listing. "
            "\n"
            "LAYOUT REQUIREMENTS: "
            "1. PRODUCT: Product displayed beautifully — hero shot, slightly angled or in context. "
            "2. EMOTIONAL DIRECTION: Follow the specified direction: "
            "   - 'Emotional': Warm colors, soft focus background, evoke feeling of joy/satisfaction. "
            "   - 'Inspirational': Bold composition, dramatic lighting, aspirational mood. "
            "   - 'Brand Storytelling': Logo prominent, brand colors dominant, 'about us' feel. "
            "3. HEADLINE: Render the custom closing headline text (if provided) in large, "
            "   elegant typography — centered or bottom-third. "
            "4. BRAND LOGO: Prominently displayed. "
            "5. BACKGROUND: Rich, atmospheric — gradient, bokeh, or lifestyle scene. "
            "\n"
            "CRITICAL TEXT RULES: "
            "- If a custom headline is provided, render it EXACTLY as given. "
            "- DO NOT invent slogans, taglines, or any text not provided. "
            "- If no headline provided, do NOT add any text — just the visual composition. "
            "\n"
            "QUALITY: Premium brand campaign quality — this is the final impression."
        ),
    },
}


def slot_default(slot_name: str) -> str:
    """Get default instructions for a slot."""
    return SLOT_TEMPLATES.get(slot_name, {}).get("instructions", "Marketplace-ready marketing image.")


def get_slot_title(slot_name: str) -> str:
    """Get display title for a slot."""
    return SLOT_TEMPLATES.get(slot_name, {}).get("title", slot_name)
