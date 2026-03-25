from __future__ import annotations

import base64
import io
import mimetypes
from pathlib import Path

import httpx


def is_data_url(value: str | None) -> bool:
    return bool(value and value.startswith("data:"))


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    lower = value.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def is_existing_file_path(value: str | None) -> bool:
    if not value or is_data_url(value) or is_http_url(value):
        return False
    try:
        path = Path(value)
        return path.exists() and path.is_file()
    except OSError:
        return False


def is_supported_image_source(value: str | None) -> bool:
    return bool(value) and (is_data_url(value) or is_http_url(value) or is_existing_file_path(value))


def parse_data_url(data_url: str) -> tuple[str, bytes]:
    if not is_data_url(data_url):
        raise ValueError("Not a data URL")
    header, b64 = data_url.split(",", 1)
    mime = header.split(";")[0].replace("data:", "") or "image/png"
    return mime, base64.b64decode(b64)


def encode_bytes_as_data_url(mime: str, content: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"


def read_local_image(path_value: str) -> tuple[str, bytes]:
    path = Path(path_value)
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/png"
    return mime, path.read_bytes()


async def load_image_bytes(image_source: str) -> tuple[str, bytes]:
    if is_data_url(image_source):
        return parse_data_url(image_source)

    if is_http_url(image_source):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(image_source)
            resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/png").split(";")[0] or "image/png"
        return mime, resp.content

    if is_existing_file_path(image_source):
        return read_local_image(image_source)

    raise ValueError("Unsupported image source. Expected data URL, http(s) URL, or existing local file path.")


def _require_pillow():
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - environment
        raise RuntimeError("Pillow is required for image composition. Install Pillow>=10.0.0.") from exc
    return Image


async def load_pil_image(image_source: str):
    image_cls = _require_pillow()
    _, image_bytes = await load_image_bytes(image_source)
    image = image_cls.open(io.BytesIO(image_bytes))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    return image


def pil_image_to_bytes(image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def pil_image_to_data_url(image, mime: str = "image/png") -> str:
    return encode_bytes_as_data_url(mime, pil_image_to_bytes(image, fmt="PNG"))
