from __future__ import annotations
import httpx
import logging
from urllib.parse import quote

from app.core.config import Settings

logger = logging.getLogger(__name__)


class AIClient:
    """Nano Banana (Gemini image) client with placeholder fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.nano_banana_api_key
        self.model = settings.nano_banana_model
        self.base_url = str(settings.nano_banana_base_url).rstrip("/")

    async def generate_image(self, prompt: str, size: str | None = None, model: str | None = None) -> str:
        """Generate an image; returns a data URL or placeholder."""
        if not self.api_key:
            return self._placeholder(prompt, size)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        url = f"{self.base_url}/models/{model or self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, params=params, json=payload)
                if resp.status_code != 200:
                    logger.warning(
                        "Nano Banana HTTP %s: %s", resp.status_code, resp.text[:500]
                    )
                    resp.raise_for_status()

                data = resp.json()
                parts = data["candidates"][0]["content"]["parts"]
                inline = next((p["inlineData"] for p in parts if "inlineData" in p), None)
                if not inline:
                    raise RuntimeError("No inlineData image returned from provider")
                b64 = inline.get("data")
                mime = inline.get("mimeType", "image/png")
                if not b64:
                    raise RuntimeError("Image payload missing base64 data")
                return f"data:{mime};base64,{b64}"
        except Exception as exc:  # pragma: no cover - external
            logger.warning("Nano Banana image generation failed (%s); returning placeholder", exc)
            return self._placeholder(prompt, size)

    def _placeholder(self, prompt: str, size: str | None) -> str:
        safe_prompt = quote(prompt)[:80]
        dims = (size or self.settings.image_size)
        # Force PNG output to avoid SVG placeholders
        return f"https://placehold.co/{dims}.png?text={safe_prompt}"

    @staticmethod
    def _parse_size(size: str) -> tuple[int, int]:
        try:
            w, h = size.lower().split("x")
            return int(w), int(h)
        except Exception:
            return 1024, 1024
