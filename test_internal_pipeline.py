from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.schemas.brand import BrandCI
from app.schemas.generation import Asset, ImageGenerationRequest
from app.schemas.image import ImageBrief
from app.schemas.product import ProductInfo
from app.schemas.project import ProjectSetup
from app.schemas.style_template import StyleTemplate
from app.services.image_generation import ImageGenerationService
from app.services.image_source_utils import encode_bytes_as_data_url
from app.services.job_store import InMemoryJobStore


async def run_smoke() -> None:
    settings = get_settings()
    service = ImageGenerationService(settings, InMemoryJobStore())
    source_bytes = Path("cup.png").read_bytes()
    source_url = encode_bytes_as_data_url("image/png", source_bytes)

    async def fake_ensure_ready():
        return None

    async def fake_generate_image(prompt, size=None, model=None, input_images=None):
        return source_url

    async def fake_product_analysis(*args, **kwargs):
        return {
            "visual_style": "clean commercial studio",
            "lighting": "soft studio light",
            "background": "light neutral background",
            "composition": "product left with clean negative space",
            "must_avoid": ["badges", "garbled text"],
            "usp_visual_strategy": {"double wall": "material cutaway"},
        }

    async def fake_review(*args, **kwargs):
        return {"score": 0.9, "issues": [], "suggestion": "ok"}

    service.ai_client.ensure_ready = fake_ensure_ready
    service.ai_client.generate_image = fake_generate_image
    service.product_analyst.run = fake_product_analysis
    service.quality_reviewer.review = fake_review

    payload = ImageGenerationRequest(
        project=ProjectSetup(
            project_name="Cup Project",
            brand_name="BrandX",
            product_category="Drinkware",
            target_marketplaces=["amazon"],
        ),
        brand=BrandCI(
            logo_url=None,
            primary_color="#1f4b99",
            secondary_color="#edf2ff",
            font_heading="Inter",
            font_body="Inter",
        ),
        product=ProductInfo(
            sku="SKU-1",
            title="Ceramic Cup",
            short_description="Double wall ceramic coffee cup",
            usps=["Double Wall", "Ceramic Finish", "Gift Ready"],
            keywords={},
            languages=["en"],
        ),
        assets=[Asset(type="product_photo", url=source_url)],
        image_briefs=[
            ImageBrief(
                slot_name="key_facts",
                instructions="Create key facts image",
                emphasis=["Double Wall", "Ceramic Finish", "Gift Ready"],
                style="modern",
            )
        ],
        remove_background=False,
        style_template=StyleTemplate.MODERN,
    )

    job_id, meta = await service.generate(payload)
    job = service.get_status(job_id)

    assert job is not None
    assert job.status == "completed"
    assert job.images and len(job.images) == 1
    assert Path(job.images[0].file_path).exists()
    assert meta["pipeline"]["slot_plans"][0]["copy_plan"]["callouts"] == [
        "Double Wall",
        "Ceramic Finish",
        "Gift Ready",
    ]
    assert meta["pipeline"]["provider_health"]["openai_image_ready"] is True

    print("INTERNAL PIPELINE OK")


if __name__ == "__main__":
    asyncio.run(run_smoke())
