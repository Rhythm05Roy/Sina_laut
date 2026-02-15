from __future__ import annotations
import httpx
import logging
from urllib.parse import quote
from typing import List, Optional

from app.core.config import Settings

logger = logging.getLogger(__name__)


def parse_data_url(data_url: str) -> tuple[str, str]:
    """Parse a data URL into mime type and base64 data."""
    if not data_url.startswith("data:"):
        raise ValueError("Not a data URL")
    # format: data:<mime>;base64,<data>
    header, b64 = data_url.split(",", 1)
    mime = header.split(";")[0].replace("data:", "")
    return mime, b64


class AIClient:
    """Nano Banana (Gemini image) client with placeholder fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.active_api_key
        self.model = settings.active_model
        self.base_url = settings.active_base_url.rstrip("/")

    async def generate_image(
        self,
        prompt: str,
        size: str | None = None,
        model: str | None = None,
        input_images: Optional[List[str]] = None,
    ) -> str:
        """Generate an image with optional input images for multi-modal generation.
        
        Args:
            prompt: Text prompt describing the image to generate
            size: Image size (e.g., "1024x1024")
            model: Model override
            input_images: List of data URLs for product images/logos to include
        
        Returns:
            Data URL of the generated image or placeholder URL
        """
        if not self.api_key:
            return self._placeholder(prompt, size)

        # Build multi-modal parts: text + images
        parts = [{"text": prompt}]
        
        # Add input images as inlineData parts
        if input_images:
            for img_url in input_images:
                if img_url and img_url.startswith("data:"):
                    try:
                        mime, b64 = parse_data_url(img_url)
                        parts.append({
                            "inlineData": {
                                "mimeType": mime,
                                "data": b64
                            }
                        })
                        logger.info("Added input image to request (%s)", mime)
                    except Exception as e:
                        logger.warning("Failed to parse input image: %s", e)

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        url = f"{self.base_url}/models/{model or self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, params=params, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.warning(
                        "Nano Banana HTTP %s: %s", resp.status_code, resp.text[:500]
                    )
                    resp.raise_for_status()

                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                inline = next((p.get("inlineData") for p in parts if "inlineData" in p), None)
                if not inline:
                    logger.warning("Nano Banana response missing inlineData; returning placeholder. Raw: %s", str(data)[:400])
                    return self._placeholder(prompt, size)
                b64 = inline.get("data")
                mime = inline.get("mimeType", "image/png")
                if not b64:
                    logger.warning("Nano Banana inlineData missing base64 data; returning placeholder.")
                    return self._placeholder(prompt, size)
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
