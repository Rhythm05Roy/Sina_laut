from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import Settings
from app.services.image_source_utils import load_image_bytes

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_BACKOFF = 2


class AIClient:
    """OpenAI GPT Image client used only for final image generation/refinement."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.openai_api_key
        self.model = settings.openai_image_model
        self.base_url = str(settings.openai_base_url).rstrip("/")
        self._ready_checked = False
        self._ready_ok = False
        self._ready_error = None
        logger.info(
            "AIClient initialized - provider=openai, model=%s, api_key=%s",
            self.model,
            "SET" if self.api_key else "MISSING",
        )

    async def ensure_ready(self) -> None:
        if self._ready_checked:
            if not self._ready_ok:
                raise RuntimeError(self._ready_error or "OpenAI image key not authorized")
            return
        if not self.api_key:
            self._ready_checked = True
            self._ready_ok = False
            self._ready_error = "OPENAI_API_KEY missing"
            raise RuntimeError(self._ready_error)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/models/{self.model}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            self._ready_checked = True
            if resp.status_code == 200:
                self._ready_ok = True
                return
            self._ready_ok = False
            self._ready_error = f"OpenAI image model rejected (HTTP {resp.status_code}): {resp.text[:300]}"
            raise RuntimeError(self._ready_error)
        except Exception as exc:
            self._ready_checked = True
            self._ready_ok = False
            self._ready_error = f"OpenAI image key check failed: {exc}"
            raise RuntimeError(self._ready_error)

    async def generate_image(
        self,
        prompt: str,
        size: str | None = None,
        model: str | None = None,
        input_images: Optional[list[str]] = None,
    ) -> str:
        await self.ensure_ready()

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                if input_images:
                    return await self._edit_image(prompt, size=size, model=model, input_images=input_images)
                return await self._generate_image(prompt, size=size, model=model)
            except httpx.TimeoutException:
                last_error = f"Request timed out (attempt {attempt + 1})"
                logger.warning(last_error)
            except Exception as exc:  # pragma: no cover - external
                last_error = str(exc)
                logger.error("OpenAI image request failed (attempt %d): %s", attempt + 1, exc)

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF * (attempt + 1))

        logger.error("All retries exhausted. Last error: %s", last_error)
        raise RuntimeError(last_error or "OpenAI image generation failed")

    async def _generate_image(self, prompt: str, size: str | None, model: str | None) -> str:
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "size": size or self.settings.image_size,
            "quality": "high",
        }
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:800]}")
        data = resp.json()
        return self._extract_data_url(data)

    async def _edit_image(
        self,
        prompt: str,
        size: str | None,
        model: str | None,
        input_images: list[str],
    ) -> str:
        files = []
        for idx, image_source in enumerate(input_images):
            if not image_source:
                continue
            try:
                mime, image_bytes = await load_image_bytes(image_source)
            except Exception as exc:
                logger.warning("Skipping invalid OpenAI edit input image %r: %s", image_source, exc)
                continue
            ext = mime.split("/")[-1] or "png"
            files.append(("image[]", (f"input_{idx}.{ext}", image_bytes, mime)))

        if not files:
            logger.info("No valid edit input images available. Falling back to fresh OpenAI generation.")
            return await self._generate_image(prompt, size=size, model=model)

        data = {
            "model": model or self.model,
            "prompt": prompt,
            "size": size or self.settings.image_size,
            "quality": "high",
        }
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self.base_url}/images/edits",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=data,
                files=files,
            )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:800]}")
        return self._extract_data_url(resp.json())

    def _extract_data_url(self, payload: dict) -> str:
        images = payload.get("data") or []
        if not images:
            raise RuntimeError("OpenAI image API returned no images")
        first = images[0]
        b64 = first.get("b64_json")
        if not b64:
            raise RuntimeError("OpenAI image API returned no b64_json payload")
        return f"data:image/png;base64,{b64}"
