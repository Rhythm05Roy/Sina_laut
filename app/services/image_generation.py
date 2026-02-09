from __future__ import annotations
import uuid
from typing import List

from app.core.config import Settings
from app.schemas.generation import ImageGenerationRequest
from app.schemas.image import GeneratedImage
from app.schemas.style_template import StyleTemplate
from app.services.ai_client import AIClient
from app.services.background_removal import remove_background
from app.services.keyword_crawler import crawl_keywords
from app.services.prompt_builder import build_prompt
from app.services.job_store import InMemoryJobStore
from app.services.storage import save_image


class ImageGenerationService:
    def __init__(self, settings: Settings, jobs: InMemoryJobStore) -> None:
        self.settings = settings
        self.ai_client = AIClient(settings)
        self.jobs = jobs

    async def generate(self, payload: ImageGenerationRequest) -> str:
        job_id = str(uuid.uuid4())
        self.jobs.create(job_id, status="queued")

        # Step 1: optional background removal on assets
        processed_assets = []
        for asset in payload.assets:
            if payload.remove_background:
                cleaned_url, changed = await remove_background(asset.url)
            else:
                cleaned_url, changed = asset.url, False
            processed_assets.append((asset.type, cleaned_url, changed))

        # Step 2: keyword enrichment
        keywords = await crawl_keywords(payload.product)

        # Step 3: Collect input images for multi-modal generation
        input_images: List[str] = []
        
        # Add processed product photo(s)
        for asset_type, cleaned_url, changed in processed_assets:
            if cleaned_url:
                input_images.append(cleaned_url)
        
        # Add brand logo if provided
        if payload.brand.logo_url:
            input_images.append(payload.brand.logo_url)

        # Step 4: prompt + image generation with style template
        images: List[GeneratedImage] = []
        for brief in payload.image_briefs:
            prompt = build_prompt(
                payload.project, 
                payload.brand, 
                payload.product, 
                brief, 
                keywords,
                style_template=payload.style_template  # Pass style template
            )
            image_url = await self.ai_client.generate_image(
                prompt, 
                size=self.settings.image_size,
                input_images=input_images
            )
            file_path = await save_image(image_url, self.settings.output_dir, f"{job_id}_{brief.slot_name}.png")
            images.append(
                GeneratedImage(
                    slot_name=brief.slot_name,
                    prompt=prompt,
                    image_url=image_url,
                    file_path=file_path,
                    background_removed=any(changed for _, _, changed in processed_assets),
                )
            )

        self.jobs.set_images(job_id, images)
        self.jobs.set_status(job_id, "completed")
        return job_id

    async def refine(self, payload: ImageGenerationRequest, feedback: str) -> str:
        job_id = str(uuid.uuid4())
        self.jobs.create(job_id, status="queued")

        keywords = await crawl_keywords(payload.product)

        # Collect input images for multi-modal generation
        input_images: List[str] = []
        
        # Add product photo(s)
        for asset in payload.assets:
            if asset.url:
                input_images.append(asset.url)
        
        # Add brand logo if provided
        if payload.brand.logo_url:
            input_images.append(payload.brand.logo_url)

        images: List[GeneratedImage] = []
        for brief in payload.image_briefs:
            prompt = build_prompt(
                payload.project, 
                payload.brand, 
                payload.product, 
                brief, 
                keywords, 
                feedback=feedback,
                style_template=payload.style_template  # Pass style template
            )
            image_url = await self.ai_client.generate_image(
                prompt, 
                size=self.settings.image_size,
                input_images=input_images
            )
            file_path = await save_image(image_url, self.settings.output_dir, f"{job_id}_{brief.slot_name}.png")
            images.append(
                GeneratedImage(
                    slot_name=brief.slot_name,
                    prompt=prompt,
                    image_url=image_url,
                    file_path=file_path,
                    background_removed=False,
                )
            )

        self.jobs.set_images(job_id, images)
        self.jobs.set_status(job_id, "completed")
        return job_id

    def get_status(self, job_id: str):
        return self.jobs.get(job_id)
