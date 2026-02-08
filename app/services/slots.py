from typing import Dict, List

SLOT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "main_product": {
        "title": "Main Image",
        "instructions": "Center the product on neutral or white background. Amazon/Google compliant. No extra graphics."
    },
    "key_facts": {
        "title": "Key Facts",
        "instructions": "Add four concise fact chips or badges. Keep typography readable. Balanced layout."
    },
    "lifestyle": {
        "title": "Lifestyle",
        "instructions": "Place product in natural use-case scene. Include three short info callouts with keyword relevance."
    },
    "usps": {
        "title": "USPs",
        "instructions": "Highlight top unique selling points with visual overlays or labels. Keep product dominant."
    },
    "cross_selling": {
        "title": "Cross-Selling",
        "instructions": "Create collage of up to six related products; optional article numbers. Consistent lighting."
    },
    "closing": {
        "title": "Closing",
        "instructions": "Summarize the value; world-building scene; include a CTA/question."
    },
    "comparison": {
        "title": "Comparison",
        "instructions": "Show what this product does better than competitors; clear side-by-side or checklist."
    },
}


def slot_default(slot_name: str) -> str:
    return SLOT_TEMPLATES.get(slot_name, {}).get("instructions", "Marketplace-ready marketing image.")
