from __future__ import annotations

import math
import logging
from pathlib import Path
from typing import Iterable

from app.schemas.brand import BrandCI
from app.services.background_removal import remove_background
from app.services.image_source_utils import load_pil_image, pil_image_to_data_url
from app.services.pipeline_models import SlotPlan

logger = logging.getLogger(__name__)


class ImageCompositor:
    async def compose_main_product(self, image_url: str, *, canvas_size: tuple[int, int] = (1024, 1024)) -> str:
        base = await load_pil_image(image_url)
        Image, _, ImageDraw, _ = self._pil_modules()
        width, height = canvas_size

        # Preserve original product pixels; only scale and place on white canvas.
        product = base.convert("RGBA")
        bbox = product.getbbox()
        if bbox:
            product = product.crop(bbox)

        target_w = int(width * 0.78)
        target_h = int(height * 0.78)
        scale = min(target_w / max(product.size[0], 1), target_h / max(product.size[1], 1))
        new_size = (
            max(1, int(product.size[0] * scale)),
            max(1, int(product.size[1] * scale)),
        )
        product = product.resize(new_size, Image.LANCZOS)

        canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))

        # Soft contact shadow to avoid a flat cutout look.
        shadow = Image.new("RGBA", (new_size[0], max(24, new_size[1] // 7)), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((0, 0, shadow.size[0], shadow.size[1]), fill=(0, 0, 0, 72))
        shadow = shadow.resize((int(shadow.size[0] * 0.92), shadow.size[1]), Image.LANCZOS)

        x = (width - new_size[0]) // 2
        y = (height - new_size[1]) // 2 - max(12, height // 40)
        shadow_x = (width - shadow.size[0]) // 2
        shadow_y = y + new_size[1] - max(8, shadow.size[1] // 2)

        canvas.alpha_composite(shadow, (shadow_x, shadow_y))
        canvas.alpha_composite(product, (x, y))
        return pil_image_to_data_url(canvas)

    async def compose(
        self,
        image_url: str | None,
        slot_plan: SlotPlan,
        brand: BrandCI,
        *,
        hero_image_url: str | None = None,
        raw_product_url: str | None = None,
        related_image_urls: list[str] | None = None,
    ) -> str:
        if slot_plan.slot_name == "main_product" or not slot_plan.copy_plan.overlay_enabled:
            return image_url or hero_image_url or raw_product_url or ""

        Image, ImageColor, ImageDraw, ImageFont = self._pil_modules()

        primary = self._normalize_color(brand.primary_color, "#1f4b99", ImageColor)
        secondary = self._normalize_color(brand.secondary_color, "#edf2ff", ImageColor)
        text_dark = (25, 32, 48, 255)
        white = (255, 255, 255, 255)

        slot = slot_plan.slot_name
        if slot == "lifestyle" and image_url:
            base = await load_pil_image(image_url)
            canvas = base.convert("RGBA")
        else:
            canvas = self._create_template_canvas((1024, 1024), primary, secondary, slot)

        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        margin = max(24, width // 24)

        heading_font = self._font(max(26, width // 24), bold=True, ImageFont=ImageFont)
        body_font = self._font(max(18, width // 42), bold=False, ImageFont=ImageFont)
        small_font = self._font(max(15, width // 54), bold=False, ImageFont=ImageFont)

        if slot == "key_facts":
            await self._paste_hero_cutout(
                canvas,
                hero_image_url=hero_image_url,
                raw_product_url=raw_product_url,
                box=(int(width * 0.06), int(height * 0.16), int(width * 0.50), int(height * 0.88)),
            )
            self._compose_key_facts(draw, width, height, margin, slot_plan.copy_plan.callouts[:4], primary, secondary, text_dark, white, heading_font, body_font)
        elif slot == "lifestyle":
            await self._paste_lifestyle_product(
                canvas,
                hero_image_url=hero_image_url,
                raw_product_url=raw_product_url,
                box=(int(width * 0.12), int(height * 0.24), int(width * 0.42), int(height * 0.78)),
            )
            self._compose_lifestyle(draw, width, height, margin, slot_plan.copy_plan.callouts[:3], primary, text_dark, white, body_font, small_font)
        elif slot == "usps":
            await self._paste_hero_cutout(
                canvas,
                hero_image_url=hero_image_url,
                raw_product_url=raw_product_url,
                box=(int(width * 0.27), int(height * 0.12), int(width * 0.73), int(height * 0.84)),
            )
            self._compose_usps(draw, width, height, margin, slot_plan.copy_plan, primary, secondary, text_dark, white, heading_font, body_font)
        elif slot == "comparison":
            await self._paste_hero_panel(canvas, hero_image_url, (margin, margin, width - margin, int(height * 0.48)))
            self._compose_comparison(draw, width, height, margin, slot_plan.copy_plan, primary, text_dark, white, heading_font, body_font)
        elif slot == "cross_selling":
            await self._paste_hero_panel(canvas, hero_image_url, (margin, margin, int(width * 0.52), int(height * 0.45)))
            await self._compose_cross_selling(
                canvas,
                draw,
                width,
                height,
                margin,
                slot_plan.copy_plan.product_labels[:6],
                related_image_urls or [],
                primary,
                text_dark,
                white,
                heading_font,
                small_font,
            )
        elif slot == "closing":
            await self._paste_hero_cutout(
                canvas,
                hero_image_url=hero_image_url,
                raw_product_url=raw_product_url,
                box=(int(width * 0.46), int(height * 0.12), int(width * 0.88), int(height * 0.84)),
            )
            self._compose_closing(draw, width, height, margin, slot_plan.copy_plan.closing_line or "", primary, white, heading_font)

        if brand.logo_url and slot_plan.visual_plan.logo_allowed:
            try:
                canvas = await self._paste_logo(canvas, brand.logo_url, margin)
            except Exception as exc:
                logger.warning("Skipping logo overlay: %s", exc)

        return pil_image_to_data_url(canvas)

    def _pil_modules(self):
        from PIL import Image, ImageColor, ImageDraw, ImageFont

        return Image, ImageColor, ImageDraw, ImageFont

    def _normalize_color(self, color: str | None, fallback: str, image_color_module):
        try:
            return image_color_module.getrgb(color if color and color.startswith("#") else f"#{color}") + (255,)
        except Exception:
            return image_color_module.getrgb(fallback) + (255,)

    def _font(self, size: int, *, bold: bool, ImageFont):
        candidates = []
        if bold:
            candidates.extend([
                "DejaVuSans-Bold.ttf",
                "arialbd.ttf",
                str(Path("C:/Windows/Fonts/arialbd.ttf")),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ])
        else:
            candidates.extend([
                "DejaVuSans.ttf",
                "arial.ttf",
                str(Path("C:/Windows/Fonts/arial.ttf")),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ])
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _wrap_text(self, draw, text: str, font, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return []
        lines = []
        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if draw.textlength(test, font=font) <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_card(self, draw, box, fill, shadow, radius=24):
        x1, y1, x2, y2 = box
        draw.rounded_rectangle((x1 + 4, y1 + 6, x2 + 4, y2 + 6), radius=radius, fill=shadow)
        draw.rounded_rectangle(box, radius=radius, fill=fill)

    def _create_template_canvas(self, size, primary, secondary, slot_name):
        Image, _, ImageDraw, _ = self._pil_modules()
        width, height = size
        canvas = Image.new("RGBA", size, (247, 248, 251, 255))
        draw = ImageDraw.Draw(canvas)
        if slot_name == "closing":
            top = self._mix_rgba((16, 27, 54, 255), primary, 0.18)
            bottom = self._mix_rgba((92, 83, 188, 255), secondary, 0.10)
        elif slot_name == "key_facts":
            top = (251, 252, 255, 255)
            bottom = self._mix_rgba((232, 238, 252, 255), secondary, 0.12)
        elif slot_name == "usps":
            top = self._mix_rgba((232, 241, 255, 255), primary, 0.14)
            bottom = self._mix_rgba((234, 226, 255, 255), secondary, 0.18)
        elif slot_name == "comparison":
            top = (252, 252, 254, 255)
            bottom = self._mix_rgba((244, 247, 255, 255), secondary, 0.16)
        elif slot_name == "cross_selling":
            top = (252, 251, 248, 255)
            bottom = self._mix_rgba((244, 247, 251, 255), secondary, 0.12)
        else:
            top = self._mix_rgba((255, 255, 255, 255), primary, 0.04)
            bottom = self._mix_rgba((250, 251, 255, 255), secondary, 0.08)
        for y in range(height):
            t = y / max(height - 1, 1)
            fill = self._mix_rgba(top, bottom, t)
            draw.line((0, y, width, y), fill=fill, width=1)
        if slot_name == "key_facts":
            draw.ellipse((int(width * 0.01), int(height * 0.18), int(width * 0.52), int(height * 0.86)), fill=(255, 255, 255, 152))
            draw.ellipse((int(width * 0.14), int(height * 0.08), int(width * 0.48), int(height * 0.48)), fill=(255, 255, 255, 88))
        elif slot_name == "usps":
            draw.ellipse((int(width * 0.05), int(height * 0.18), int(width * 0.58), int(height * 0.88)), fill=(255, 255, 255, 104))
        elif slot_name == "comparison":
            draw.rounded_rectangle((20, 20, width - 20, height - 20), radius=34, fill=(255, 255, 255, 112))
        elif slot_name == "closing":
            draw.ellipse((int(width * 0.34), int(height * 0.16), int(width * 0.94), int(height * 0.92)), fill=(255, 255, 255, 24))
        return canvas

    def _mix_rgba(self, a, b, t: float):
        return tuple(int(a[idx] + (b[idx] - a[idx]) * t) for idx in range(4))

    async def _paste_hero_panel(self, canvas, hero_image_url: str | None, box):
        if not hero_image_url:
            return
        Image, _, ImageDraw, _ = self._pil_modules()
        draw = ImageDraw.Draw(canvas)
        x1, y1, x2, y2 = box
        self._draw_card(draw, box, (255, 255, 255, 244), (0, 0, 0, 24), radius=28)
        hero = await load_pil_image(hero_image_url)
        hero = hero.convert("RGBA")
        pad = 24
        inner = (x1 + pad, y1 + pad, x2 - pad, y2 - pad)
        hero = self._fit_image(hero, (inner[2] - inner[0], inner[3] - inner[1]), Image.LANCZOS)
        paste_x = inner[0] + max(0, (inner[2] - inner[0] - hero.size[0]) // 2)
        paste_y = inner[1] + max(0, (inner[3] - inner[1] - hero.size[1]) // 2)
        canvas.alpha_composite(hero, (paste_x, paste_y))

    async def _paste_hero_cutout(self, canvas, *, hero_image_url: str | None, raw_product_url: str | None, box):
        Image, _, ImageDraw, _ = self._pil_modules()
        product = await self._load_product_cutout(hero_image_url, raw_product_url)
        if product is None:
            await self._paste_hero_panel(canvas, hero_image_url, box)
            return
        x1, y1, x2, y2 = box
        product = self._fit_image(product, (x2 - x1, y2 - y1), Image.LANCZOS)
        shadow_h = max(24, product.size[1] // 9)
        shadow = Image.new("RGBA", (int(product.size[0] * 0.72), shadow_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((0, 0, shadow.size[0], shadow.size[1]), fill=(0, 0, 0, 52))
        px = x1 + max(0, ((x2 - x1) - product.size[0]) // 2)
        py = y1 + max(0, ((y2 - y1) - product.size[1]) // 2)
        sx = px + (product.size[0] - shadow.size[0]) // 2
        sy = py + product.size[1] - shadow.size[1] // 2
        canvas.alpha_composite(shadow, (sx, sy))
        canvas.alpha_composite(product, (px, py))

    async def _paste_lifestyle_product(self, canvas, *, hero_image_url: str | None, raw_product_url: str | None, box):
        Image, _, ImageDraw, _ = self._pil_modules()
        product = await self._load_product_cutout(hero_image_url, raw_product_url)
        if product is None:
            await self._paste_hero_panel(canvas, hero_image_url, box)
            return
        x1, y1, x2, y2 = box
        product = self._fit_image(product, (x2 - x1, y2 - y1), Image.LANCZOS)
        shadow_h = max(28, product.size[1] // 8)
        shadow = Image.new("RGBA", (int(product.size[0] * 0.8), shadow_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((0, 0, shadow.size[0], shadow.size[1]), fill=(0, 0, 0, 76))
        px = x1 + max(0, ((x2 - x1) - product.size[0]) // 2)
        py = y1 + max(0, ((y2 - y1) - product.size[1]) // 2)
        sx = px + (product.size[0] - shadow.size[0]) // 2
        sy = py + product.size[1] - shadow.size[1] // 2
        canvas.alpha_composite(shadow, (sx, sy))
        canvas.alpha_composite(product, (px, py))

    async def _load_product_cutout(self, hero_image_url: str | None, raw_product_url: str | None):
        if hero_image_url:
            try:
                hero = await load_pil_image(hero_image_url)
                hero = hero.convert("RGBA")
                hero_cutout = await self._remove_background_from_pil(hero)
                if hero_cutout is not None:
                    alpha = hero_cutout.getchannel("A")
                    bbox = alpha.getbbox()
                    if bbox:
                        return hero_cutout.crop(bbox)
                cutout = self._make_transparent_from_white(hero)
                alpha = cutout.getchannel("A")
                bbox = alpha.getbbox()
                if bbox and self._bbox_is_reasonable(bbox, cutout.size):
                    return cutout.crop(bbox)
            except Exception:
                pass
        if raw_product_url:
            try:
                raw = await load_pil_image(raw_product_url)
                raw = raw.convert("RGBA")
                cutout = await self._remove_background_from_pil(raw)
                if cutout is None:
                    cutout = self._make_transparent_from_white(raw)
                alpha = cutout.getchannel("A")
                bbox = alpha.getbbox()
                if bbox and self._bbox_is_reasonable(bbox, cutout.size):
                    cutout = cutout.crop(bbox)
                return cutout
            except Exception:
                return None
        return None

    async def _remove_background_from_pil(self, image):
        try:
            cleaned_url, changed = await remove_background(pil_image_to_data_url(image))
            if not changed:
                return None
            cutout = await load_pil_image(cleaned_url)
            return cutout.convert("RGBA")
        except Exception:
            return None

    def _bbox_is_reasonable(self, bbox, size):
        x1, y1, x2, y2 = bbox
        width, height = size
        bbox_w = max(1, x2 - x1)
        bbox_h = max(1, y2 - y1)
        return (bbox_w / max(width, 1)) < 0.92 and (bbox_h / max(height, 1)) < 0.95

    def _make_transparent_from_white(self, image):
        rgba = image.copy().convert("RGBA")
        pixels = rgba.load()
        width, height = rgba.size
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if r > 242 and g > 242 and b > 242 and max(r, g, b) - min(r, g, b) < 18:
                    pixels[x, y] = (r, g, b, 0)
        return rgba

    def _fit_image(self, image, target_size, resample):
        width, height = target_size
        scale = min(width / max(image.size[0], 1), height / max(image.size[1], 1))
        return image.resize(
            (
                max(1, int(image.size[0] * scale)),
                max(1, int(image.size[1] * scale)),
            ),
            resample,
        )

    def _draw_text_block(self, draw, text_lines: Iterable[str], start_xy, font, fill, line_gap=8):
        x, y = start_xy
        for line in text_lines:
            draw.text((x, y), line, font=font, fill=fill)
            bbox = draw.textbbox((x, y), line, font=font)
            y = bbox[3] + line_gap

    def _compose_key_facts(self, draw, width, height, margin, callouts, primary, secondary, text_dark, white, heading_font, body_font):
        if not callouts:
            return
        image_font = self._pil_modules()[3]
        eyebrow_font = self._font(max(14, width // 68), bold=False, ImageFont=image_font)
        sub_font = self._font(max(16, width // 52), bold=False, ImageFont=image_font)
        card_font = self._font(max(18, width // 40), bold=True, ImageFont=image_font)
        draw.text((margin, margin), "PRODUCT HIGHLIGHTS", font=eyebrow_font, fill=(*primary[:3], 178))
        draw.text((margin, margin + 22), "Key Facts", font=heading_font, fill=text_dark)
        draw.text(
            (margin, margin + 62),
            "Fast-scanning feature snapshot for marketplace shoppers.",
            font=sub_font,
            fill=(92, 102, 122, 255),
        )

        region_x1 = int(width * 0.57)
        region_y1 = int(height * 0.18)
        card_w = width - region_x1 - margin
        card_gap = 18
        card_count = max(1, min(4, len(callouts)))
        available_h = height - region_y1 - margin - card_gap * (card_count - 1)
        card_h = max(108, int(available_h / card_count))
        for idx, text in enumerate(callouts[:card_count]):
            y1 = region_y1 + idx * (card_h + card_gap)
            y2 = y1 + card_h
            box = (region_x1, y1, region_x1 + card_w, y2)
            fill = (255, 255, 255, 246)
            shadow = (33, 42, 58, 18)
            self._draw_card(draw, box, fill, shadow, radius=24)
            draw.rounded_rectangle(box, radius=24, outline=(226, 231, 240, 255), width=2)

            accent = primary if idx % 2 == 0 else secondary
            draw.rounded_rectangle((region_x1 + 22, y1 + 22, region_x1 + 30, y2 - 22), radius=4, fill=accent)
            tag = f"0{idx + 1}" if idx < 9 else str(idx + 1)
            draw.text((region_x1 + 48, y1 + 20), tag, font=eyebrow_font, fill=(100, 110, 132, 255))
            lines = self._wrap_text(draw, text, card_font, card_w - 92)
            self._draw_text_block(draw, lines[:3], (region_x1 + 48, y1 + 46), card_font, text_dark, line_gap=6)

    def _compose_lifestyle(self, draw, width, height, margin, callouts, primary, text_dark, white, body_font, small_font):
        if not callouts:
            return
        image_font = self._pil_modules()[3]
        eyebrow_font = self._font(max(13, width // 78), bold=False, ImageFont=image_font)
        title_font = self._font(max(24, width // 34), bold=True, ImageFont=image_font)
        panel_x1 = margin
        panel_x2 = int(width * 0.74)
        panel_y2 = height - margin
        panel_y1 = panel_y2 - max(150, height // 5)
        draw.rounded_rectangle((panel_x1, panel_y1, panel_x2, panel_y2), radius=30, fill=(255, 255, 255, 214))
        draw.text((panel_x1 + 22, panel_y1 + 18), "REAL-WORLD USE", font=eyebrow_font, fill=(*primary[:3], 176))
        draw.text((panel_x1 + 22, panel_y1 + 42), callouts[0], font=title_font, fill=text_dark)

        chip_x = panel_x1 + 22
        chip_y = panel_y1 + 94
        chip_gap = 12
        for line in callouts[1:3]:
            text_w = int(draw.textlength(line, font=small_font))
            chip_w = min(panel_x2 - panel_x1 - 44, text_w + 34)
            chip_h = 34
            draw.rounded_rectangle(
                (chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
                radius=16,
                fill=(255, 255, 255, 228),
                outline=(226, 231, 240, 255),
                width=2,
            )
            draw.text((chip_x + 16, chip_y + 8), line, font=small_font, fill=text_dark)
            chip_x += chip_w + chip_gap

    def _compose_usps(self, draw, width, height, margin, copy_plan, primary, secondary, text_dark, white, heading_font, body_font):
        if not copy_plan.callouts and not copy_plan.headline:
            return
        image_font = self._pil_modules()[3]
        eyebrow_font = self._font(max(14, width // 68), bold=False, ImageFont=image_font)
        card_font = self._font(max(17, width // 48), bold=True, ImageFont=image_font)
        positions = [
            (margin, int(height * 0.18), int(width * 0.30), int(height * 0.32)),
            (int(width * 0.70), int(height * 0.18), width - margin, int(height * 0.32)),
            (margin, int(height * 0.60), int(width * 0.30), int(height * 0.74)),
            (int(width * 0.70), int(height * 0.60), width - margin, int(height * 0.74)),
        ]
        draw.text((margin, margin), "WHY IT STANDS OUT", font=eyebrow_font, fill=(*primary[:3], 182))
        if copy_plan.headline:
            lines = self._wrap_text(draw, copy_plan.headline, heading_font, width - margin * 2)
            self._draw_text_block(draw, lines[:2], (margin, margin + 22), heading_font, text_dark, line_gap=4)
        target_x = width // 2
        target_y = int(height * 0.49)
        callout_y_shift = 0 if not copy_plan.headline else 44
        for idx, line in enumerate(copy_plan.callouts[:4]):
            x1, y1, x2, y2 = positions[idx]
            y1 += callout_y_shift
            y2 += callout_y_shift
            box = (x1, y1, x2, y2)
            accent = primary if idx % 2 == 0 else secondary
            if x1 < target_x:
                start = (x2, (y1 + y2) // 2)
            else:
                start = (x1, (y1 + y2) // 2)
            draw.line((start[0], start[1], target_x, target_y), fill=accent, width=3)
            self._draw_card(draw, box, (255, 255, 255, 240), (48, 56, 72, 18), radius=22)
            accent = primary if idx % 2 == 0 else secondary
            draw.rounded_rectangle((x1 + 14, y1 + 14, x1 + 28, y2 - 14), radius=6, fill=accent)
            tag = f"0{idx + 1}" if idx < 9 else str(idx + 1)
            draw.text((x1 + 40, y1 + 16), tag, font=eyebrow_font, fill=(100, 110, 132, 255))
            wrapped = self._wrap_text(draw, line, card_font, (x2 - x1) - 52)
            self._draw_text_block(draw, wrapped[:2], (x1 + 40, y1 + 40), card_font, text_dark, line_gap=5)

    def _compose_comparison(self, draw, width, height, margin, copy_plan, primary, text_dark, white, heading_font, body_font):
        if not copy_plan.comparison_left and not copy_plan.comparison_right:
            return
        board = (margin, int(height * 0.58), width - margin, height - margin)
        draw.rounded_rectangle(board, radius=26, fill=(255, 255, 255, 234))
        x_mid = (board[0] + board[2]) // 2
        draw.line((x_mid, board[1] + 64, x_mid, board[3] - 24), fill=(214, 219, 230, 255), width=3)
        draw.text((board[0] + 28, board[1] + 20), "Our Product", font=heading_font, fill=primary)
        draw.text((x_mid + 28, board[1] + 20), "Others", font=heading_font, fill=text_dark)
        for idx, text in enumerate(copy_plan.comparison_left[:3]):
            y = board[1] + 86 + idx * 56
            draw.text((board[0] + 28, y), f"+ {text}", font=body_font, fill=primary)
        for idx, text in enumerate(copy_plan.comparison_right[:3]):
            y = board[1] + 86 + idx * 56
            draw.text((x_mid + 28, y), f"- {text}", font=body_font, fill=(160, 48, 48, 255))

    async def _compose_cross_selling(self, canvas, draw, width, height, margin, labels, related_image_urls, primary, text_dark, white, heading_font, small_font):
        if not labels:
            return
        Image, _, _, _ = self._pil_modules()
        grid_top = int(height * 0.56)
        draw.text((margin, grid_top - 44), "Related Products", font=heading_font, fill=primary)
        cols = 3
        rows = 2
        cell_w = (width - margin * 2 - 20 * (cols - 1)) // cols
        cell_h = max(116, (height - grid_top - margin - 16 * (rows - 1)) // rows)
        for idx, label in enumerate(labels[:6]):
            row = idx // cols
            col = idx % cols
            x1 = margin + col * (cell_w + 20)
            y1 = grid_top + row * (cell_h + 16)
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            self._draw_card(draw, (x1, y1, x2, y2), (255, 255, 255, 236), (0, 0, 0, 22), radius=22)
            image_height = max(0, cell_h - 54)
            if idx < len(related_image_urls):
                try:
                    related = await load_pil_image(related_image_urls[idx])
                    related = related.convert("RGBA")
                    related = self._fit_image(related, (cell_w - 28, image_height - 8), Image.LANCZOS)
                    px = x1 + (cell_w - related.size[0]) // 2
                    py = y1 + 10 + max(0, (image_height - related.size[1]) // 2)
                    canvas.alpha_composite(related, (px, py))
                except Exception:
                    pass
            lines = self._wrap_text(draw, label, small_font, cell_w - 24)
            self._draw_text_block(draw, lines[:2], (x1 + 12, y2 - 34), small_font, text_dark, line_gap=2)

    def _compose_closing(self, draw, width, height, margin, line, primary, white, heading_font):
        if not line:
            return
        title_font = self._font(max(40, width // 14), bold=True, ImageFont=self._pil_modules()[3])
        lines = self._wrap_text(draw, line, title_font, int(width * 0.38))
        current_y = int(height * 0.18)
        for wrapped in lines[:3]:
            draw.text((margin, current_y), wrapped, font=title_font, fill=white)
            current_y = draw.textbbox((margin, current_y), wrapped, font=title_font)[3] + 10
        draw.rounded_rectangle((margin, current_y + 18, margin + 170, current_y + 24), radius=4, fill=(255, 255, 255, 190))

    async def _paste_logo(self, canvas, logo_url: str, margin: int):
        Image, _, _, _ = self._pil_modules()
        logo = await load_pil_image(logo_url)
        logo = logo.convert("RGBA")
        target_w = max(96, canvas.size[0] // 7)
        scale = target_w / max(1, logo.size[0])
        target_h = max(42, int(logo.size[1] * scale))
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        x = canvas.size[0] - target_w - margin
        y = margin
        canvas.alpha_composite(logo, (x, y))
        return canvas
