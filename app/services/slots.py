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


def build_followup_suggestions(project, brand, product, main_image_url: str | None = None, style_template: str = "playful") -> dict:
    """
    Create lightweight, human-readable prompt seeds for slots 2-7
    using the uploaded main product photo + stored context.
    This is heuristic (no real vision analysis) but keeps prompts consistent.
    """
    cat = getattr(project, "product_category", "") or getattr(product, "product_category", "") or "the product"

    # Helpers
    def top_items(items, n=4):
        return [i for i in items if i][:n]

    key_facts = top_items(product.usps, 4) or [
        f"Crisp detail of {cat}",
        "Highlight build quality",
        "Show key accessory in frame",
        "Emphasize scale/size clearly",
    ]

    lifestyle_scene = (
        f"{product.title} being used naturally in a setting that matches its category ({cat}). "
        "Keep product as hero; warm, realistic lighting. Use the uploaded main product photo as reference."
    )

    usp_list = top_items(product.usps, 4) or key_facts

    advantages = usp_list[:3] or ["Premium build", "Easy setup", "Trusted brand"]
    limitations = ["Generic alternatives feel cheaper", "Shorter warranty elsewhere", "Inconsistent reviews"]

    cross_sell = [
        f"{cat} - bundle pack",
        f"{cat} - travel size",
        f"{cat} - premium edition",
        f"{cat} - accessory A",
        f"{cat} - accessory B",
        f"{cat} - gift set",
    ]

    closing_headline = f"{project.brand_name}: Ready for {project.product_category} excellence?"

    return {
        "key_facts": {
            "facts": key_facts,
            "prompt": (
                "Product left, four branded fact cards on right. "
                f"Use main product photo{' '+main_image_url if main_image_url else ''} as reference. "
                f"Style {style_template}. Facts: {', '.join(key_facts)}."
            )
        },
        "lifestyle": {
            "scenario": lifestyle_scene,
            "prompt": f"Lifestyle scene: {lifestyle_scene}"
        },
        "usps": {
            "usps": usp_list,
            "prompt": f"Center product; surround with callouts for: {', '.join(usp_list)}."
        },
        "comparison": {
            "advantages": advantages,
            "limitations": limitations,
            "prompt": (
                "Split left/right. Left = Our Product (green) with advantages. "
                "Right = Others (red) with limitations. "
                f"Advantages: {', '.join(advantages)}. Limitations: {', '.join(limitations)}."
            )
        },
        "cross_selling": {
            "product_names": cross_sell,
            "prompt": f"3x2 grid of related items. Include: {', '.join(cross_sell)}."
        },
        "closing": {
            "headline": closing_headline,
            "prompt": (
                f"Final emotional image, direction: Emotional. "
                f'Headline: "{closing_headline}". Brand colors {brand.primary_color}/{brand.secondary_color}.'
            )
        }
    }
