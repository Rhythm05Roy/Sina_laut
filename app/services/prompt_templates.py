from __future__ import annotations
from typing import Dict, Any

# Master system prompt to be prepended for GPT-driven prompt generation
MASTER_PROMPT = """
You are a senior e-commerce product image director and prompt engineer.
Your task is to generate a highly optimized image generation prompt for Nano Banana based on structured product data.
You must:
1) Analyze product category
2) Consider target marketplace image compliance rules
3) Adapt visual style based on price positioning (budget, mid-range, premium)
4) Decide lighting, composition, camera style
5) Decide what must be avoided
6) Adjust style depending on image type (main / infographic / lifestyle)
STRICT RULES:
- For Amazon main image: pure white background (#FFFFFF), no text, no logos outside product, no graphics, no gradients, no props.
- For lifestyle image: realistic environment matching target audience.
- For infographic image: clean marketing layout, highlight USP visually.
- Avoid cinematic, dramatic, unrealistic rendering unless premium lifestyle.
- Avoid AI-art style wording.
- Use realistic commercial photography language.
- Include camera details for realism.
- Mention materials and textures naturally.
- Prevent floating unrealistic shadows unless stylistically required.
Output ONLY the final optimized Nano Banana prompt. Do not explain reasoning. Do not output analysis.
""".strip()


# Category templates: base text for main and lifestyle/infographic as applicable
CATEGORY_TEMPLATES: Dict[str, Dict[str, str]] = {
    "footwear": {
        "main": (
            "Ultra-realistic e-commerce studio product photography of {name}, breathable mesh upper, detailed stitching, "
            "ergonomic sole, 45-degree side angle, centered composition, pure white seamless background #FFFFFF, "
            "soft even commercial lighting, natural contact shadow beneath shoe, sharp focus, shot with 85mm lens, "
            "f/11 aperture, ISO 100, realistic materials, Amazon compliant, no text, no watermark"
        ),
        "lifestyle": (
            "Professional lifestyle photography of {name} worn by {audience}, {scenario}, natural daylight, realistic shadows, "
            "modern athletic aesthetic, shallow depth of field, commercial sports brand style, high detail, sharp focus"
        ),
        "infographic": (
            "Professional Amazon infographic of {name}, dynamic angled composition, clean bright neutral background, bold modern typography, "
            "minimal monochrome icons, sharp focus, commercial marketing layout"
        )
    },
    "beauty": {
        "main": (
            "High-resolution studio product photography of {name}, clean packaging design, centered composition, pure white background #FFFFFF, "
            "soft diffused lighting, minimal shadow, ultra-sharp detail, cosmetic commercial photography style, Amazon compliant"
        ),
        "lifestyle": (
            "Close-up beauty lifestyle photography of {name} applied on skin, natural window lighting, soft skin texture detail, "
            "clean bathroom vanity setting, realistic tone, premium cosmetic brand aesthetic"
        )
    },
    "electronics": {
        "main": (
            "Professional catalog photography of {name}, sleek modern design, front and angled perspective, pure white background #FFFFFF, "
            "balanced soft lighting, crisp reflections, realistic material finish, ultra-sharp detail, commercial e-commerce style"
        ),
        "lifestyle": (
            "Modern lifestyle photography of {name} in use by {audience}, minimal contemporary interior, natural lighting, "
            "realistic reflections, high-end tech advertising style"
        )
    },
    "home_kitchen": {
        "main": (
            "Professional studio product photography of {name}, neutral tone, centered layout, pure white background #FFFFFF, "
            "soft diffused lighting, realistic material texture, clean catalog presentation, ultra-sharp detail"
        ),
        "lifestyle": (
            "Lifestyle photography of {name} placed in modern home kitchen environment, warm natural lighting, realistic shadows, "
            "cozy premium interior aesthetic, high-resolution commercial style"
        )
    },
    "apparel": {
        "main": (
            "High-resolution studio product photography of {name}, neatly displayed, wrinkle-free fabric, centered composition, "
            "pure white seamless background #FFFFFF, soft even lighting, sharp fabric texture detail, Amazon compliant"
        ),
        "lifestyle": (
            "Professional fashion lifestyle photography of {name} worn by {audience}, natural outdoor light, "
            "realistic body posture, premium fashion campaign style, shallow depth of field"
        )
    },
    "health": {
        "main": (
            "Clean commercial product photography of {name} bottle, label clearly visible, centered composition, pure white background #FFFFFF, "
            "soft balanced lighting, sharp detail, clinical clean aesthetic, Amazon compliant"
        )
    }
}


PRICE_STYLE: Dict[str, str] = {
    "budget": "Simple lighting, clean minimal composition, avoid luxury wording.",
    "mid": "Soft edge highlights, slight depth of field, balanced contrast.",
    "premium": "Subtle rim light, controlled reflections, high contrast but realistic, premium commercial look."
}


MARKETPLACE_RULES: Dict[str, Dict[str, Any]] = {
    "amazon": {
        "main": "Pure white (#FFFFFF), no text, no props, no extra logos, no gradients. Compliant hero packshot.",
        "infographic": "Clean marketing layout; keep text crisp and minimal; avoid busy badges; maintain professional spacing.",
        "lifestyle": "Realistic setting matching audience; avoid overt brand clutter."
    },
    "shopify": {
        "main": "Creative allowed but keep product hero clear; allow soft color backdrops.",
        "infographic": "Brand storytelling allowed; tasteful color blocks.",
        "lifestyle": "Creative, on-brand storytelling encouraged."
    },
    "flipkart": {
        "main": "White or very light neutral; minimal text; avoid props.",
        "infographic": "Clean layout, limited text.",
        "lifestyle": "Realistic environment; modest styling."
    }
}
