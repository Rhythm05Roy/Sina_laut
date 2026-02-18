from __future__ import annotations
from typing import Dict, Any


class VisualDirector:
    """
    Agent 2 — Visual Director
    Decides per-slot strategy (main/infographic/lifestyle/etc) based on analysis.
    """

    @staticmethod
    def decide(slot_name: str, analysis: Dict[str, Any] | None) -> Dict[str, Any]:
        # Defaults per slot
        if slot_name == "main_product":
            base = {
                "image_type": "main",
                "background": "pure white #FFFFFF (no gradient, no texture)",
                "text_allowed": False,
                "logo_allowed": False,
                "icons_allowed": False,
                "composition": "centered product, 85% frame, straight-on or 45-degree",
                "must_avoid": ["gradient backgrounds", "floating UI badges", "overlays", "logos not provided by user"],
            }
        elif slot_name == "key_facts":
            base = {
                "image_type": "infographic",
                "text_allowed": True,   # but optional; AI may omit if it hurts professionalism
                "icons_allowed": False,
                "background": "clean neutral or subtle brand tint; soft gradient allowed if very light and professional",
                "composition": "product dominant; optional minimal fact bullets in a column",
                "badge_style": "no badges; simple text bullets",
                "max_callouts": 3,
                "must_avoid": ["circular neon badges", "illegible text", "invented logos", "busy overlays"],
            }
        elif slot_name == "lifestyle":
            base = {
                "image_type": "lifestyle",
                "text_allowed": False,
                "composition": "hero product in real environment",
            }
        else:
            base = {
                "image_type": "infographic",
                "text_allowed": True,
                "icons_allowed": False,
                "background": "clean white or subtle brand tint",
                "badge_style": "flat rectangular cards",
            }

        if analysis:
            base["visual_style"] = analysis.get("visual_style")
            base["lighting"] = analysis.get("lighting")
            base["background"] = analysis.get("background", base.get("background"))
            base["composition"] = analysis.get("composition", base.get("composition"))
            base["must_avoid"] = analysis.get("must_avoid", base.get("must_avoid", []))
            base["usp_visual_strategy"] = analysis.get("usp_visual_strategy", {})
        return base
