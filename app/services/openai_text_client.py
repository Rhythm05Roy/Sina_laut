from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import Settings
from app.services.image_source_utils import encode_bytes_as_data_url, load_image_bytes

logger = logging.getLogger(__name__)


class OpenAITextClient:
    """OpenAI multimodal text client for image-aware analysis prompts."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_analysis_model
        self.base_url = str(settings.openai_base_url).rstrip("/")

    async def _normalize_image_input(self, image_url: Optional[str]) -> Optional[str]:
        if not image_url:
            return None
        try:
            mime, image_bytes = await load_image_bytes(image_url)
            return encode_bytes_as_data_url(mime, image_bytes)
        except Exception as exc:
            logger.info("Skipping OpenAI analysis image attachment: %s", exc)
            return None

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        image_url: Optional[str] = None,
        temperature: float = 0.4,
        max_output_tokens: int = 500,
    ) -> Optional[str]:
        if not self.api_key:
            return None

        content: list[dict[str, Any]] = []
        if user_prompt:
            content.append({"type": "text", "text": user_prompt})

        normalized_image = await self._normalize_image_input(image_url)
        if normalized_image:
            content.append({"type": "image_url", "image_url": {"url": normalized_image}})

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content or [{"type": "text", "text": user_prompt or "Analyze this context."}]},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if resp.status_code >= 400:
                logger.warning(
                    "OpenAI text generation failed (HTTP %s): %s",
                    resp.status_code,
                    resp.text[:500],
                )
                return None
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message", {})
            text = message.get("content")
            if isinstance(text, str):
                return text.strip() or None
            if isinstance(text, list):
                texts = [item.get("text", "") for item in text if isinstance(item, dict) and item.get("text")]
                output = "\n".join(texts).strip()
                return output or None
            return None
        except Exception as exc:
            logger.warning("OpenAI text generation failed: %s", exc)
            return None

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        image_url: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: int = 500,
    ) -> Optional[dict[str, Any]]:
        if not self.api_key:
            return None

        content: list[dict[str, Any]] = []
        if user_prompt:
            content.append({"type": "text", "text": user_prompt})

        normalized_image = await self._normalize_image_input(image_url)
        if normalized_image:
            content.append({"type": "image_url", "image_url": {"url": normalized_image}})

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content or [{"type": "text", "text": user_prompt or "Return valid JSON."}]},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if resp.status_code >= 400:
                logger.warning(
                    "OpenAI JSON generation failed (HTTP %s): %s",
                    resp.status_code,
                    resp.text[:500],
                )
                return None
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message", {})
            output = message.get("content")
            if isinstance(output, list):
                output = "\n".join(
                    item.get("text", "") for item in output if isinstance(item, dict) and item.get("text")
                ).strip()
            if not isinstance(output, str) or not output.strip():
                return None
            return json.loads(output)
        except Exception as exc:
            logger.warning("OpenAI JSON decode failed: %s", exc)
            return None
