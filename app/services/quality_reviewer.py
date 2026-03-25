from __future__ import annotations
from typing import Optional, Dict, Any

from app.core.config import Settings
from app.services.openai_text_client import OpenAITextClient


class QualityReviewer:
    """
    Optional quality review loop using OpenAI vision.
    Scores compliance and realism and suggests fixes.
    """

    def __init__(self, settings: Settings):
        self.client = OpenAITextClient(settings)

    async def review(self, image_url: str, slot_name: str) -> Optional[Dict[str, Any]]:
        if not self.client.api_key or not image_url:
            return None

        sys = (
            "You are a marketplace image QA assistant. Inspect the image and rate compliance for "
            "background cleanliness, lighting realism, presence of unwanted text/graphics, "
            "and overall professional look. Score 0-1 and explain briefly."
        )
        user = (
            f"Slot: {slot_name}\n"
            "Return JSON: {\"score\": float 0-1, \"issues\": [..], \"suggestion\": \"...\"}"
        )

        return await self.client.generate_json(
            system_prompt=sys,
            user_prompt=user,
            image_url=image_url,
            temperature=0.2,
            max_output_tokens=220,
        )
