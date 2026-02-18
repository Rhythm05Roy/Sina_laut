from __future__ import annotations
import httpx
import logging
from typing import Optional, Dict, Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


class QualityReviewer:
    """
    Optional quality review loop using GPT-4o vision.
    Scores compliance and realism; suggests fixes.
    """

    def __init__(self, settings: Settings):
        self.api_key = settings.openai_api_key
        self.model = "gpt-4o-mini"

    async def review(self, image_url: str, slot_name: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or not image_url.startswith("data:"):
            return None  # keep simple: only review inline data to avoid remote fetches

        sys = (
            "You are a marketplace image QA assistant. Inspect the image and rate compliance for "
            "background cleanliness, lighting realism, presence of unwanted text/graphics, "
            "and overall professional look. Score 0-1."
        )
        user = (
            f"Slot: {slot_name}\n"
            "Return JSON: {\"score\": float 0-1, \"issues\": [..], \"suggestion\": \"...\"}"
        )

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": sys},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user},
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
                    ],
                },
            ],
            "max_tokens": 200,
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            import json
            return json.loads(content) if content else None
        except Exception as exc:  # pragma: no cover - external
            logger.warning("QualityReviewer failed: %s", exc)
            return None
