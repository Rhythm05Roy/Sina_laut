from typing import Dict, List

SLOT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "main_product": {
        "title": "Main Image",
        "instructions": (
            "Create a professional e-commerce product listing image. "
            "LAYOUT REQUIREMENTS: "
            "1. Place the PROVIDED product image CENTERED on a clean white/neutral background. "
            "2. At the TOP: Display the brand logo (if provided) centered. "
            "3. At the BOTTOM: Show 4 circular badges in a horizontal row containing key product facts "
            "(e.g., age rating like '4+', piece count like '72 pieces', feature icons with brief labels). "
            "4. Use the brand's primary and secondary colors for the circular badges and accent elements. "
            "5. Include a prominent product tagline or title below the product. "
            "STYLE: Professional product photography, Amazon/Google listing compliant, clean and premium look. "
            "CRITICAL: Use the actual product image provided - do NOT generate a different product."
        )
    },
    "key_facts": {
        "title": "Key Facts",
        "instructions": (
            "Create an informational product image with key facts layout. "
            "LAYOUT REQUIREMENTS: "
            "1. Place the PROVIDED product image on the LEFT side (about 60% of image). "
            "2. At the TOP: Display brand logo and sub-brand logo (if applicable). "
            "3. On the RIGHT side: Display 4 circular info badges stacked vertically with icons and text "
            "showing key product facts (features, specifications, benefits). "
            "4. Use brand colors for the info badges - primary color for background, text in white or secondary color. "
            "5. Include small descriptive icons inside or next to each badge. "
            "STYLE: Professional infographic style, clean typography, visually balanced. "
            "CRITICAL: Incorporate the provided product image - do NOT create a new product."
        )
    },
    "lifestyle": {
        "title": "Lifestyle",
        "instructions": (
            "Create a lifestyle scene showing the product in use. "
            "LAYOUT REQUIREMENTS: "
            "1. Show a realistic scene of a child/person happily using/playing with the product. "
            "2. The PROVIDED product should be clearly visible and recognizable in the scene. "
            "3. Add 2-3 floating info callout boxes or labels highlighting key features. "
            "4. Include product dimensions or size reference if applicable. "
            "5. Use warm, inviting lighting - natural home environment or appropriate setting. "
            "STYLE: Lifestyle photography, warm and engaging, relatable family/play moments. "
            "CRITICAL: The product in the scene should match the provided product image."
        )
    },
    "usps": {
        "title": "USPs",
        "instructions": (
            "Create an image highlighting Unique Selling Points (USPs). "
            "LAYOUT REQUIREMENTS: "
            "1. Product image featured prominently (center or left side). "
            "2. Display 3-5 USP cards/badges with icons and brief text descriptions. "
            "3. Use visual connectors (lines, arrows) pointing from USP badges to relevant product areas. "
            "4. Brand logo at top corner. "
            "5. Use brand colors for USP badges and visual elements. "
            "STYLE: Clean marketing infographic, easy to scan, professional. "
            "CRITICAL: Use the provided product image."
        )
    },
    "cross_selling": {
        "title": "Cross-Selling",
        "instructions": (
            "Create a cross-selling collage image. "
            "LAYOUT REQUIREMENTS: "
            "1. Main product featured larger in center or primary position. "
            "2. Display 4-6 related/complementary products in a grid or collage around the main product. "
            "3. Include 'Discover more' or similar CTA text. "
            "4. Add brand logo and product line name. "
            "5. Optional: Include article numbers or product names below each item. "
            "STYLE: Clean product collage, consistent lighting and styling across all items. "
            "CRITICAL: Main product should match the provided product image."
        )
    },
    "closing": {
        "title": "Closing",
        "instructions": (
            "Create a closing/summary image. "
            "LAYOUT REQUIREMENTS: "
            "1. Product featured in an aspirational world-building scene. "
            "2. Include a compelling CTA question or statement (e.g., 'Ready to start the adventure?'). "
            "3. Summarize key value proposition in 1-2 short lines. "
            "4. Brand logo prominently displayed. "
            "5. Use brand colors for text overlays and accents. "
            "STYLE: Inspirational, premium feel, drives purchase intent."
        )
    },
    "comparison": {
        "title": "Comparison",
        "instructions": (
            "Create a comparison image showing product advantages. "
            "LAYOUT REQUIREMENTS: "
            "1. Side-by-side or checklist comparison format. "
            "2. Show what this product does better than alternatives. "
            "3. Use checkmarks, X marks, or rating scales for clear visual comparison. "
            "4. Product image on one side, comparison elements on the other. "
            "5. Brand colors for positive highlights. "
            "STYLE: Clear comparison chart/infographic, easy to understand at a glance."
        )
    },
}


def slot_default(slot_name: str) -> str:
    return SLOT_TEMPLATES.get(slot_name, {}).get("instructions", "Marketplace-ready marketing image.")
