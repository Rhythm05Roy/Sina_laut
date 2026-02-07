from __future__ import annotations
from typing import Tuple

async def remove_background(image_url: str) -> Tuple[str, bool]:
    """Placeholder background removal.

    In production, plug in something like rembg, Clipdrop, or Remove.bg.
    Returns the processed image URL and whether a change was made.
    """
    return image_url, False
