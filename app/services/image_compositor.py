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
            await self._paste_hero_panel(canvas, hero_image_url, (margin, margin, int(width * 0.57), height - margin))
            self._compose_key_facts(draw, width, height, margin, slot_plan.copy_plan.callouts[:4], primary, secondary, text_dark, white, heading_font, body_font)
        elif slot == "lifestyle":
            await self._paste_lifestyle_product(
                canvas,
                hero_image_url=hero_image_url,
                raw_product_url=raw_product_url,
                box=(int(width * 0.12), int(height * 0.18), int(width * 0.48), int(height * 0.84)),
            )
            self._compose_lifestyle(draw, width, height, margin, slot_plan.copy_plan.callouts[:3], primary, text_dark, white, body_font, small_font)
        elif slot == "usps":
            await self._paste_hero_panel(canvas, hero_image_url, (margin, margin, int(width * 0.57), height - margin))
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
            await self._paste_hero_panel(canvas, hero_image_url, (int(width * 0.18), margin, int(width * 0.82), int(height * 0.62)))
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
        draw.rounded_rectangle((x1 + 8, y1 + 10, x2 + 8, y2 + 10), radius=radius, fill=shadow)
        draw.rounded_rectangle(box, radius=radius, fill=fill)

    def _create_template_canvas(self, size, primary, secondary, slot_name):
        Image, _, ImageDraw, _ = self._pil_modules()
        width, height = size
        canvas = Image.new("RGBA", size, (247, 248, 251, 255))
        draw = ImageDraw.Draw(canvas)
        top = self._mix_rgba((255, 255, 255, 255), primary, 0.06)
        bottom = self._mix_rgba((255, 255, 255, 255), secondary, 0.08)
        for y in range(height):
            t = y / max(height - 1, 1)
            fill = self._mix_rgba(top, bottom, t)
            draw.line((0, y, width, y), fill=fill, width=1)
        panel_fill = (255, 255, 255, 120)
        if slot_name in {"comparison", "closing"}:
            draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=36, fill=panel_fill)
        else:
            draw.rounded_rectangle((28, 28, width - 28, height - 28), radius=30, fill=(255, 255, 255, 100))
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

    async def _paste_lifestyle_product(self, canvas, *, hero_image_url: str | None, raw_product_url: str | None, box):
        Image, _, ImageDraw, _ = self._pil_modules()
        product = await self._load_product_cutout(raw_product_url, hero_image_url)
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

    async def _load_product_cutout(self, raw_product_url: str | None, hero_image_url: str | None):
        candidate = raw_product_url or hero_image_url
        if not candidate:
            return None
        try:
            cleaned, _ = await remove_background(candidate)
            cutout = await load_pil_image(cleaned)
            cutout = cutout.convert("RGBA")
            alpha = cutout.getchannel("A")
            bbox = alpha.getbbox()
            if bbox:
                cutout = cutout.crop(bbox)
            return cutout
        except Exception:
            return None

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
        region_x1 = int(width * 0.61)
        card_w = width - region_x1 - margin
        card_h = max(110, int((height - margin * 5) / 4))
        for idx, text in enumerate(callouts[:4]):
            y1 = margin + idx * (card_h + 12)
            y2 = y1 + card_h
            box = (region_x1, y1, region_x1 + card_w, y2)
            fill = (255, 255, 255, 238)
            shadow = (0, 0, 0, 24)
            self._draw_card(draw, box, fill, shadow, radius=20)
            accent = primary if idx % 2 == 0 else secondary
            draw.rounded_rectangle((region_x1 + 14, y1 + 16, region_x1 + 28, y2 - 16), radius=8, fill=accent)
            lines = self._wrap_text(draw, text, heading_font, card_w - 58)
            self._draw_text_block(draw, lines[:3], (region_x1 + 42, y1 + 24), heading_font, text_dark, line_gap=6)

    def _compose_lifestyle(self, draw, width, height, margin, callouts, primary, text_dark, white, body_font, small_font):
        if not callouts:
            return
        strip_h = max(150, height // 5)
        y1 = height - strip_h - margin
        overlay = (255, 255, 255, 216)
        draw.rounded_rectangle((margin, y1, width - margin, height - margin), radius=28, fill=overlay)
        title = "Marketplace Highlights"
        draw.text((margin + 20, y1 + 16), title, font=body_font, fill=text_dark)
        for idx, line in enumerate(callouts[:3]):
            bullet_y = y1 + 58 + idx * 30
            draw.text((margin + 24, bullet_y), f"- {line}", font=small_font, fill=primary)

    def _compose_usps(self, draw, width, height, margin, copy_plan, primary, secondary, text_dark, white, heading_font, body_font):
        x1 = int(width * 0.62)
        panel_w = width - x1 - margin
        current_y = margin
        if copy_plan.headline:
            self._draw_card(draw, (x1, current_y, x1 + panel_w, current_y + 96), (255, 255, 255, 244), (0, 0, 0, 24), radius=24)
            draw.rounded_rectangle((x1 + 14, current_y + 16, x1 + 28, current_y + 80), radius=7, fill=primary)
            lines = self._wrap_text(draw, copy_plan.headline, heading_font, panel_w - 32)
            self._draw_text_block(draw, lines[:2], (x1 + 42, current_y + 22), heading_font, text_dark, line_gap=4)
            current_y += 112
        for idx, line in enumerate(copy_plan.callouts[:3]):
            box = (x1, current_y, x1 + panel_w, current_y + 92)
            self._draw_card(draw, box, (255, 255, 255, 240), (0, 0, 0, 22), radius=22)
            accent = primary if idx % 2 == 0 else secondary
            draw.rounded_rectangle((x1 + 14, current_y + 16, x1 + 26, current_y + 76), radius=6, fill=accent)
            wrapped = self._wrap_text(draw, line, body_font, panel_w - 48)
            self._draw_text_block(draw, wrapped[:2], (x1 + 40, current_y + 24), body_font, text_dark, line_gap=5)
            current_y += 108

    def _compose_comparison(self, draw, width, height, margin, copy_plan, primary, text_dark, white, heading_font, body_font):
        if not copy_plan.comparison_left and not copy_plan.comparison_right:
            return
        board = (margin, int(height * 0.58), width - margin, height - margin)
        draw.rounded_rectangle(board, radius=26, fill=(255, 255, 255, 232))
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
        strip_h = max(110, height // 7)
        y1 = height - strip_h - margin
        draw.rounded_rectangle((margin, y1, width - margin, height - margin), radius=28, fill=primary)
        lines = self._wrap_text(draw, line, heading_font, width - margin * 3)
        line_height = draw.textbbox((0, 0), "Ag", font=heading_font)[3]
        total_h = len(lines[:2]) * line_height + (len(lines[:2]) - 1) * 8
        current_y = y1 + (strip_h - total_h) // 2
        for wrapped in lines[:2]:
            text_w = draw.textlength(wrapped, font=heading_font)
            draw.text(((width - text_w) / 2, current_y), wrapped, font=heading_font, fill=white)
            current_y += line_height + 8

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
