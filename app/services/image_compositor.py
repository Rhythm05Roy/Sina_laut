from __future__ import annotations

import math
import logging
from pathlib import Path
from typing import Iterable

from app.schemas.brand import BrandCI
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

    async def compose(self, image_url: str, slot_plan: SlotPlan, brand: BrandCI) -> str:
        if slot_plan.slot_name == "main_product" or not slot_plan.copy_plan.overlay_enabled:
            return image_url

        base = await load_pil_image(image_url)
        Image, ImageColor, ImageDraw, ImageFont = self._pil_modules()
        canvas = base.convert("RGBA")
        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        margin = max(24, width // 24)

        primary = self._normalize_color(brand.primary_color, "#1f4b99", ImageColor)
        secondary = self._normalize_color(brand.secondary_color, "#edf2ff", ImageColor)
        text_dark = (25, 32, 48, 255)
        white = (255, 255, 255, 255)

        heading_font = self._font(max(26, width // 24), bold=True, ImageFont=ImageFont)
        body_font = self._font(max(18, width // 42), bold=False, ImageFont=ImageFont)
        small_font = self._font(max(15, width // 54), bold=False, ImageFont=ImageFont)

        slot = slot_plan.slot_name
        if slot == "key_facts":
            self._compose_key_facts(draw, width, height, margin, slot_plan.copy_plan.callouts[:4], primary, secondary, text_dark, white, heading_font, body_font)
        elif slot == "lifestyle":
            self._compose_lifestyle(draw, width, height, margin, slot_plan.copy_plan.callouts[:3], primary, text_dark, white, body_font, small_font)
        elif slot == "usps":
            self._compose_usps(draw, width, height, margin, slot_plan.copy_plan, primary, secondary, text_dark, white, heading_font, body_font)
        elif slot == "comparison":
            self._compose_comparison(draw, width, height, margin, slot_plan.copy_plan, primary, text_dark, white, heading_font, body_font)
        elif slot == "cross_selling":
            self._compose_cross_selling(draw, width, height, margin, slot_plan.copy_plan.product_labels[:6], primary, text_dark, white, heading_font, small_font)
        elif slot == "closing":
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
            fill = secondary if idx % 2 == 0 else primary
            shadow = (0, 0, 0, 35)
            self._draw_card(draw, box, fill, shadow)
            text_fill = text_dark if idx % 2 == 0 else white
            lines = self._wrap_text(draw, text, heading_font, card_w - 36)
            self._draw_text_block(draw, lines[:3], (region_x1 + 18, y1 + 20), heading_font, text_fill, line_gap=6)

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
            self._draw_card(draw, (x1, current_y, x1 + panel_w, current_y + 90), primary, (0, 0, 0, 35), radius=26)
            lines = self._wrap_text(draw, copy_plan.headline, heading_font, panel_w - 32)
            self._draw_text_block(draw, lines[:2], (x1 + 18, current_y + 20), heading_font, white, line_gap=4)
            current_y += 106
        for idx, line in enumerate(copy_plan.callouts[:3]):
            box = (x1, current_y, x1 + panel_w, current_y + 92)
            fill = secondary if idx % 2 == 0 else primary
            text_fill = text_dark if idx % 2 == 0 else white
            self._draw_card(draw, box, fill, (0, 0, 0, 28), radius=24)
            wrapped = self._wrap_text(draw, line, body_font, panel_w - 30)
            self._draw_text_block(draw, wrapped[:2], (x1 + 16, current_y + 24), body_font, text_fill, line_gap=5)
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

    def _compose_cross_selling(self, draw, width, height, margin, labels, primary, text_dark, white, heading_font, small_font):
        if not labels:
            return
        grid_top = int(height * 0.62)
        draw.text((margin, grid_top - 44), "Related Products", font=heading_font, fill=primary)
        cols = 3
        rows = 2
        cell_w = (width - margin * 2 - 20 * (cols - 1)) // cols
        cell_h = max(88, (height - grid_top - margin - 16 * (rows - 1)) // rows)
        for idx, label in enumerate(labels[:6]):
            row = idx // cols
            col = idx % cols
            x1 = margin + col * (cell_w + 20)
            y1 = grid_top + row * (cell_h + 16)
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            self._draw_card(draw, (x1, y1, x2, y2), (255, 255, 255, 236), (0, 0, 0, 22), radius=22)
            lines = self._wrap_text(draw, label, small_font, cell_w - 28)
            self._draw_text_block(draw, lines[:2], (x1 + 14, y1 + cell_h // 2 - 18), small_font, text_dark, line_gap=4)

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
