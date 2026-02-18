from __future__ import annotations
import httpx
import logging
import asyncio
import base64
from urllib.parse import quote
from typing import List, Optional

from app.core.config import Settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_BACKOFF = 2  # seconds


def parse_data_url(data_url: str) -> tuple[str, str]:
    """Parse a data URL into mime type and base64 data."""
    if not data_url.startswith("data:"):
        raise ValueError("Not a data URL")
    # format: data:<mime>;base64,<data>
    header, b64 = data_url.split(",", 1)
    mime = header.split(";")[0].replace("data:", "")
    return mime, b64


class AIClient:
    """Google Gemini image generation client with retry and error propagation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.active_api_key
        self.model = settings.active_model
        self.base_url = settings.active_base_url.rstrip("/")
        self._ready_checked = False
        self._ready_ok = False
        self._ready_error = None
        logger.info(
            "AIClient initialized — model=%s, base_url=%s, api_key=%s",
            self.model,
            self.base_url,
            "SET" if self.api_key else "MISSING",
        )

    async def ensure_ready(self) -> None:
        """Validate the key once by listing models; raise if not authorized."""
        if self._ready_checked:
            if not self._ready_ok:
                raise RuntimeError(self._ready_error or "Nano Banana key not authorized")
            return
        if not self.api_key:
            self._ready_checked = True
            self._ready_ok = False
            self._ready_error = "NANO_BANANA_API_KEY missing"
            raise RuntimeError(self._ready_error)
        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params={"key": self.api_key, "pageSize": 1})
        except Exception as exc:
            self._ready_checked = True
            self._ready_ok = False
            self._ready_error = f"Nano Banana key check failed: {exc}"
            raise RuntimeError(self._ready_error)

        self._ready_checked = True
        if resp.status_code == 200:
            self._ready_ok = True
            return
        self._ready_ok = False
        self._ready_error = f"Nano Banana key rejected (HTTP {resp.status_code}): {resp.text[:300]}"
        raise RuntimeError(self._ready_error)

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
            Data URL of the generated image

        Raises:
            RuntimeError: If generation fails after retries
        """
        await self.ensure_ready()

        # Build multi-modal parts: text + images
        parts = [{"text": prompt}]

        # Add input images as inlineData parts
        img_count = 0
        if input_images:
            for img_url in input_images:
                if img_url and img_url.startswith("data:"):
                    try:
                        mime, b64 = parse_data_url(img_url)
                        # validate base64; skip if invalid/too short
                        if len(b64) < 32:
                            raise ValueError("data URL too short")
                        base64.b64decode(b64, validate=True)
                        parts.append({
                            "inlineData": {
                                "mimeType": mime,
                                "data": b64
                            }
                        })
                        img_count += 1
                    except Exception as e:
                        logger.warning("Skipping invalid input image: %s", e)

        logger.info(
            "Generating image — model=%s, prompt_len=%d, input_images=%d",
            model or self.model,
            len(prompt),
            img_count,
        )

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        url = f"{self.base_url}/models/{model or self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    resp = await client.post(url, params=params, json=payload, headers=headers)

                    if resp.status_code == 429:
                        # Rate limited — wait and retry
                        wait = RETRY_BACKOFF * (attempt + 1)
                        logger.warning("Rate limited (429), retrying in %ds", wait)
                        await asyncio.sleep(wait)
                        continue

                    if resp.status_code != 200:
                        error_text = resp.text[:800]
                        logger.error(
                            "Gemini HTTP %s (attempt %d/%d): %s",
                            resp.status_code,
                            attempt + 1,
                            MAX_RETRIES,
                            error_text,
                        )
                        last_error = f"HTTP {resp.status_code}: {error_text}"
                        if resp.status_code >= 500:
                            # Server error — retry
                            await asyncio.sleep(RETRY_BACKOFF * (attempt + 1))
                            continue
                        # Client error (400, 403, etc.) — don't retry
                        break

                    data = resp.json()

                    # Check for blocked content
                    candidates = data.get("candidates", [])
                    if not candidates:
                        block_reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
                        last_error = f"Content blocked by safety filter: {block_reason}"
                        logger.warning("Generation blocked: %s. Raw: %s", block_reason, str(data)[:400])
                        break

                    response_parts = candidates[0].get("content", {}).get("parts", [])
                    inline = next((p.get("inlineData") for p in response_parts if "inlineData" in p), None)

                    if not inline:
                        # Model returned text only — extract any error/reasoning
                        text_parts = [p.get("text", "") for p in response_parts if "text" in p]
                        text_response = " ".join(text_parts)
                        logger.warning(
                            "No inlineData in response (attempt %d). Text: %s. Raw: %s",
                            attempt + 1,
                            text_response[:200],
                            str(data)[:400],
                        )
                        last_error = f"Model returned text instead of image: {text_response[:200]}"
                        # Retry once in case it's a fluke
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_BACKOFF)
                            continue
                        break

                    b64 = inline.get("data")
                    mime = inline.get("mimeType", "image/png")
                    if not b64:
                        last_error = "inlineData missing base64 data"
                        logger.warning("inlineData missing base64 data")
                        break

                    logger.info("Image generated successfully (attempt %d)", attempt + 1)
                    return f"data:{mime};base64,{b64}"

            except httpx.TimeoutException:
                last_error = f"Request timed out (attempt {attempt + 1})"
                logger.warning(last_error)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF)
                    continue
            except Exception as exc:
                last_error = f"Unexpected error: {exc}"
                logger.error("Generation failed (attempt %d): %s", attempt + 1, exc)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF)
                    continue

        # All retries exhausted — return placeholder with error context
        logger.error("All retries exhausted. Last error: %s", last_error)
        return self._placeholder(prompt, size)

    def _placeholder(self, prompt: str, size: str | None) -> str:
        safe_prompt = quote(prompt)[:80]
        dims = (size or self.settings.image_size)
        return f"https://placehold.co/{dims}.png?text={safe_prompt}"

    @staticmethod
    def _parse_size(size: str) -> tuple[int, int]:
        try:
            w, h = size.lower().split("x")
            return int(w), int(h)
        except Exception:
            return 1024, 1024
