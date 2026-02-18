from __future__ import annotations
import base64
import io
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


async def remove_background(image_url: str) -> Tuple[str, bool]:
    """Remove background from a product image using rembg.

    Falls back gracefully if rembg is not installed.

    Args:
        image_url: Data URL (data:image/...;base64,...) or HTTP URL

    Returns:
        Tuple of (processed_image_url, was_changed)
    """
    # Only process data URLs (inline images)
    if not image_url.startswith("data:"):
        logger.info("Background removal skipped: not a data URL")
        return image_url, False

    try:
        from rembg import remove as rembg_remove
        from PIL import Image
    except ImportError:
        logger.warning(
            "rembg or Pillow not installed — skipping background removal. "
            "Install with: pip install rembg[cpu] Pillow"
        )
        return image_url, False

    try:
        # Parse data URL
        header, b64_data = image_url.split(",", 1)
        mime = header.split(";")[0].replace("data:", "")

        # Decode image
        img_bytes = base64.b64decode(b64_data)
        input_image = Image.open(io.BytesIO(img_bytes))

        # Remove background
        output_image = rembg_remove(input_image)

        # Convert back to data URL (PNG for transparency)
        buffer = io.BytesIO()
        output_image.save(buffer, format="PNG")
        output_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        result_url = f"data:image/png;base64,{output_b64}"

        logger.info("Background removed successfully")
        return result_url, True

    except Exception as exc:
        logger.warning("Background removal failed: %s — returning original", exc)
        return image_url, False
