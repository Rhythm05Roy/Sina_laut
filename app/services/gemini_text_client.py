from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import Settings
from app.services.image_source_utils import load_image_bytes

logger = logging.getLogger(__name__)


class GeminiTextClient:
    """Thin Gemini wrapper for text, JSON, and multimodal analysis calls."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.gemini_text_api_key
        self.model = settings.gemini_text_model
        self.base_url = str(settings.gemini_base_url).rstrip("/")
        self._disabled = False

    async def _image_part(self, image_url: str) -> Optional[dict[str, Any]]:
        if not image_url:
            return None
        try:
            mime, image_bytes = await load_image_bytes(image_url)
            return {
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            }
        except ValueError:
            logger.info("Skipping Gemini image attachment for unsupported image source.")
            return None
        except Exception as exc:  # pragma: no cover - external
            logger.warning("Gemini image input conversion failed: %s", exc)
            return None

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        image_url: Optional[str] = None,
        response_mime_type: str = "text/plain",
        temperature: float = 0.4,
        max_output_tokens: int = 400,
    ) -> Optional[str]:
        if not self.api_key:
            return None
        if self._disabled:
            return None

        parts: list[dict[str, Any]] = []
        if system_prompt:
            parts.append({"text": f"System instruction:\n{system_prompt}"})
        if user_prompt:
            parts.append({"text": user_prompt})
        image_part = await self._image_part(image_url) if image_url else None
        if image_part:
            parts.append(image_part)

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": response_mime_type,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    params={"key": self.api_key},
                    json=payload,
                )
            if resp.status_code >= 400:
                if "API_KEY_INVALID" in resp.text or "API Key not found" in resp.text:
                    self._disabled = True
                logger.warning(
                    "Gemini text generation failed (HTTP %s): %s",
                    resp.status_code,
                    resp.text[:500],
                )
                return None
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [part.get("text", "") for part in parts if part.get("text")]
            output = "\n".join(texts).strip()
            return output or None
        except Exception as exc:  # pragma: no cover - external
            logger.warning("Gemini text generation failed: %s", exc)
            return None

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        image_url: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> Optional[dict[str, Any]]:
        output = await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_url=image_url,
            response_mime_type="application/json",
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if not output:
            return None
        try:
            return json.loads(output)
        except Exception as exc:  # pragma: no cover - external
            logger.warning("Gemini JSON decode failed: %s", exc)
            return None
