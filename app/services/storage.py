from __future__ import annotations
import asyncio
import base64
from pathlib import Path
from typing import Optional

import httpx


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _decode_data_url(data_url: str) -> bytes:
    # format: data:<mime>;base64,<data>
    if "," not in data_url:
        raise ValueError("Invalid data URL")
    b64_part = data_url.split(",", 1)[1]
    return base64.b64decode(b64_part)


async def save_image(url: str, output_dir: str, filename: str) -> str:
    """Save image (data URL or remote URL) to disk and return the file path."""
    out_dir = Path(output_dir)
    _ensure_dir(out_dir)
    out_path = out_dir / filename

    if url.startswith("data:image"):
        data = _decode_data_url(url)
        await asyncio.to_thread(out_path.write_bytes, data)
        return str(out_path)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        await asyncio.to_thread(out_path.write_bytes, resp.content)
    return str(out_path)
