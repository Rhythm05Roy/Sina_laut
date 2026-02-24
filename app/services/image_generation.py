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
from app.services.job_store import InMemoryJobStore
from app.services.prompt_analyzer import PromptAnalyzer
from app.services.storage import save_image
from app.services.product_analyst import ProductAnalyst
from app.services.visual_director import VisualDirector
from app.services.prompt_engineer import PromptEngineer
from app.services.quality_reviewer import QualityReviewer


class ImageGenerationService:
    def __init__(self, settings: Settings, jobs: InMemoryJobStore) -> None:
        self.settings = settings
        self.ai_client = AIClient(settings)
        self.jobs = jobs
        self.prompt_analyzer = PromptAnalyzer(settings) if settings.openai_api_key else None
        self.product_analyst = ProductAnalyst(settings) if settings.openai_api_key else None
        self.quality_reviewer = QualityReviewer(settings) if settings.openai_api_key else None

    async def generate(self, payload: ImageGenerationRequest) -> tuple[str, dict]:
        job_id = str(uuid.uuid4())
        self.jobs.create(job_id, status="queued")

        analysis_meta = {
            "analysis_used": bool(self.prompt_analyzer),
            "analysis_ok": False,
            "analysis_text": None,
            "placeholder_used": False,
            "error": None,
            "pipeline": {},
        }
        images: List[GeneratedImage] = []

        try:
            # Verify upstream key once
            await self.ai_client.ensure_ready()

            processed_assets = []
            for asset in payload.assets:
                if payload.remove_background:
                    cleaned_url, changed = await remove_background(asset.url)
                else:
                    cleaned_url, changed = asset.url, False
                processed_assets.append((asset.type, cleaned_url, changed))

            keywords = await crawl_keywords(
                payload.product,
                category=payload.project.product_category,
                marketplace=payload.project.target_marketplaces[0] if payload.project.target_marketplaces else "amazon",
                analysis=None,
            )

            input_images: List[str] = [cleaned for _, cleaned, _ in processed_assets if cleaned]
            if payload.brand.logo_url:
                input_images.append(payload.brand.logo_url)

            for brief in payload.image_briefs:
                analysis = None
                if self.product_analyst:
                    analysis = await self.product_analyst.run(
                        payload.project,
                        payload.brand,
                        payload.product,
                        marketplace=payload.project.target_marketplaces[0] if payload.project.target_marketplaces else "amazon",
                    )
                    analysis_meta["pipeline"]["product_analysis"] = analysis

                vision_guidance = None
                if self.prompt_analyzer and input_images:
                    vision_guidance = await self.prompt_analyzer.analyze(
                        input_images[0],
                        payload.project,
                        payload.brand,
                        payload.product,
                        brief.slot_name,
                    )
                    analysis_meta["analysis_ok"] = bool(vision_guidance)
                    analysis_meta["analysis_text"] = vision_guidance

                strategy = VisualDirector.decide(brief.slot_name, analysis)
                analysis_meta["pipeline"]["image_strategy"] = strategy

                # Force minimal style template for main image to avoid playful overlays
                style_tpl = StyleTemplate.MINIMAL if brief.slot_name == "main_product" else payload.style_template

                prompt = PromptEngineer.compose(
                    payload.project,
                    payload.brand,
                    payload.product,
                    brief,
                    keywords,
                    analysis,
                    strategy,
                    style_tpl,
                )
                if vision_guidance:
                    prompt = f"{vision_guidance}\n\n{prompt}"

                image_url = await self.ai_client.generate_image(
                    prompt,
                    size=self.settings.image_size,
                    input_images=input_images
                )
                if image_url.startswith("https://placehold.co/"):
                    analysis_meta["placeholder_used"] = True
                    analysis_meta["error"] = "Upstream model returned placeholder (generation failed)."

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

            if images and self.quality_reviewer and images[0].image_url:
                qa = await self.quality_reviewer.review(images[0].image_url, images[0].slot_name)
                if qa:
                    analysis_meta["pipeline"]["quality_review"] = qa
                    score = qa.get("score", 1)
                    if score < 0.5:
                        analysis_meta["error"] = f"Quality score low ({score}); issues: {qa.get('issues')}"

            # Mark failed if placeholder detected
            if analysis_meta["placeholder_used"]:
                self.jobs.set_status(job_id, "failed")
            else:
                self.jobs.set_status(job_id, "completed")
            return job_id, analysis_meta

        except Exception as exc:
            analysis_meta["error"] = f"Generation exception: {exc}"
            self.jobs.set_status(job_id, "failed")
            return job_id, analysis_meta

    async def refine(self, payload: ImageGenerationRequest, feedback: str) -> tuple[str, dict]:
        job_id = str(uuid.uuid4())
        self.jobs.create(job_id, status="queued")

        analysis_meta = {
            "analysis_used": bool(self.prompt_analyzer),
            "analysis_ok": False,
            "analysis_text": None,
            "placeholder_used": False,
            "error": None,
            "pipeline": {},
        }
        images: List[GeneratedImage] = []

        try:
            await self.ai_client.ensure_ready()
            keywords = await crawl_keywords(
                payload.product,
                category=payload.project.product_category,
                marketplace=payload.project.target_marketplaces[0] if payload.project.target_marketplaces else "amazon",
                analysis=None,
            )

            input_images: List[str] = [asset.url for asset in payload.assets if asset.url]
            if payload.brand.logo_url:
                input_images.append(payload.brand.logo_url)

            for brief in payload.image_briefs:
                analysis = None
                if self.product_analyst:
                    analysis = await self.product_analyst.run(
                        payload.project,
                        payload.brand,
                        payload.product,
                        marketplace=payload.project.target_marketplaces[0] if payload.project.target_marketplaces else "amazon",
                    )
                    analysis_meta["pipeline"]["product_analysis"] = analysis

                vision_guidance = None
                if self.prompt_analyzer and input_images:
                    vision_guidance = await self.prompt_analyzer.analyze(
                        input_images[0],
                        payload.project,
                        payload.brand,
                        payload.product,
                        brief.slot_name,
                    )
                    analysis_meta["analysis_ok"] = bool(vision_guidance)
                    analysis_meta["analysis_text"] = vision_guidance

                strategy = VisualDirector.decide(brief.slot_name, analysis)
                analysis_meta["pipeline"]["image_strategy"] = strategy

                prompt = PromptEngineer.compose(
                    payload.project,
                    payload.brand,
                    payload.product,
                    brief,
                    keywords,
                    analysis,
                    strategy,
                    payload.style_template,
                    feedback=feedback,
                )
                if vision_guidance:
                    prompt = f"{vision_guidance}\n\n{prompt}"

                image_url = await self.ai_client.generate_image(
                    prompt,
                    size=self.settings.image_size,
                    input_images=input_images
                )
                if image_url.startswith("https://placehold.co/"):
                    analysis_meta["placeholder_used"] = True
                    analysis_meta["error"] = "Upstream model returned placeholder (refinement failed)."

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
            if images and self.quality_reviewer and images[0].image_url:
                qa = await self.quality_reviewer.review(images[0].image_url, images[0].slot_name)
                if qa:
                    analysis_meta["pipeline"]["quality_review"] = qa
                    score = qa.get("score", 1)
                    if score < 0.5:
                        analysis_meta["error"] = f"Quality score low ({score}); issues: {qa.get('issues')}"

            if analysis_meta["placeholder_used"]:
                self.jobs.set_status(job_id, "failed")
            else:
                self.jobs.set_status(job_id, "completed")
            return job_id, analysis_meta

        except Exception as exc:
            analysis_meta["error"] = f"Refine exception: {exc}"
            self.jobs.set_status(job_id, "failed")
            return job_id, analysis_meta

    def get_status(self, job_id: str):
        return self.jobs.get(job_id)
