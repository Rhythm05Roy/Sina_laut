from __future__ import annotations

import uuid
from typing import List

from app.core.config import Settings
from app.schemas.generation import ImageGenerationRequest
from app.schemas.image import GeneratedImage
from app.schemas.style_template import StyleTemplate
from app.services.ai_client import AIClient
from app.services.background_removal import remove_background
from app.services.image_compositor import ImageCompositor
from app.services.image_source_utils import is_supported_image_source
from app.services.job_store import InMemoryJobStore
from app.services.keyword_crawler import crawl_keywords
from app.services.pipeline_models import KeywordPlan, ProductAnalysis, ProviderHealth, QAReview
from app.services.product_analyst import ProductAnalyst
from app.services.quality_reviewer import QualityReviewer
from app.services.slot_planner import SlotPlanner
from app.services.storage import save_image


class ImageGenerationService:
    def __init__(self, settings: Settings, jobs: InMemoryJobStore) -> None:
        self.settings = settings
        self.ai_client = AIClient(settings)
        self.jobs = jobs
        self.product_analyst = ProductAnalyst(settings) if settings.openai_api_key else None
        self.quality_reviewer = QualityReviewer(settings) if settings.openai_api_key else None
        self.slot_planner = SlotPlanner(settings) if settings.openai_api_key else None
        self.image_compositor = ImageCompositor()

    @staticmethod
    def _marketplace(payload: ImageGenerationRequest) -> str:
        return payload.project.target_marketplaces[0] if payload.project.target_marketplaces else "amazon"

    @staticmethod
    def _analysis_from_dict(raw: dict | None) -> ProductAnalysis:
        if not raw:
            return ProductAnalysis()
        return ProductAnalysis(**{key: value for key, value in raw.items() if key in ProductAnalysis.model_fields})

    @staticmethod
    def _qa_from_dict(raw: dict | None) -> QAReview | None:
        if not raw:
            return None
        try:
            return QAReview(**raw)
        except Exception:
            return None

    @staticmethod
    def _analysis_text(analysis: ProductAnalysis) -> str | None:
        parts = [analysis.visual_style, analysis.lighting, analysis.composition]
        text = " | ".join(part for part in parts if part)
        return text or None

    async def _prepare_assets(
        self, payload: ImageGenerationRequest
    ) -> tuple[list[tuple[str, str, bool]], list[str], list[str], list[str], list[str], list[str]]:
        processed_assets: list[tuple[str, str, bool]] = []
        product_images: list[str] = []
        reference_images: list[str] = []
        source_images: list[str] = []
        related_images: list[str] = []
        warnings: list[str] = []

        for asset in payload.assets:
            if not is_supported_image_source(asset.url):
                raise ValueError(
                    f"Unsupported image source for asset '{asset.type}'. Expected data URL, http(s) URL, or existing local file path."
                )
            if self._should_remove_background(payload, asset.type):
                cleaned_url, changed = await remove_background(asset.url)
            else:
                cleaned_url, changed = asset.url, False
            processed_assets.append((asset.type, cleaned_url, changed))
            if asset.type == "product_photo":
                product_images.append(cleaned_url)
            elif asset.type in {"source_photo", "main_raw", "original_product"}:
                source_images.append(cleaned_url)
            elif asset.type in {"related_product", "related_image"}:
                related_images.append(cleaned_url)
            elif asset.type in {"reference_image", "scene_reference", "ref_image"}:
                reference_images.append(cleaned_url)
            else:
                reference_images.append(cleaned_url)

        if payload.brand.logo_url:
            if not is_supported_image_source(payload.brand.logo_url):
                warnings.append("Brand logo source is invalid; logo overlay was skipped.")

        return processed_assets, product_images, reference_images, source_images, related_images, warnings

    @staticmethod
    def _dedupe_images(values: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    def _select_generation_images(
        self,
        *,
        slot_name: str,
        reference_images: list[str],
    ) -> list[str]:
        chosen: list[str] = []
        if slot_name == "lifestyle":
            chosen.extend(reference_images[:1])
        return self._dedupe_images(chosen)

    async def _build_context(
        self,
        payload: ImageGenerationRequest,
        product_images: list[str],
        source_images: list[str],
    ) -> tuple[ProductAnalysis, KeywordPlan, str | None, str | None]:
        marketplace = self._marketplace(payload)
        primary_image = next((image for image in product_images if image), None)
        source_image = next((image for image in source_images if image), None) or primary_image

        analysis = ProductAnalysis()
        if self.product_analyst:
            raw_analysis = await self.product_analyst.run(
                payload.project,
                payload.brand,
                payload.product,
                marketplace=marketplace,
                image_url=source_image,
            )
            analysis = self._analysis_from_dict(raw_analysis)

        keyword_plan = await crawl_keywords(
            payload.product,
            category=payload.project.product_category,
            marketplace=marketplace,
            analysis=analysis.model_dump(),
        )
        return analysis, keyword_plan, primary_image, source_image

    def _provider_health(self, keyword_plan: KeywordPlan, warnings: list[str]) -> ProviderHealth:
        return ProviderHealth(
            openai_image_ready=bool(self.settings.openai_api_key),
            openai_analysis_ready=bool(self.settings.openai_api_key),
            gemini_keywords_ready=keyword_plan.source == "gemini" and keyword_plan.available,
            warnings=list(warnings),
        )

    @staticmethod
    def _should_remove_background(payload: ImageGenerationRequest, asset_type: str) -> bool:
        if not payload.remove_background or asset_type != "product_photo":
            return False
        # The main image path now uses AI-based scene cleanup instead of rembg.
        return not any(brief.slot_name == "main_product" for brief in payload.image_briefs)

    async def _execute(
        self,
        payload: ImageGenerationRequest,
        *,
        feedback: str | None = None,
    ) -> tuple[str, dict]:
        job_id = str(uuid.uuid4())
        self.jobs.create(job_id, status="queued")

        analysis_meta = {
            "analysis_used": bool(self.product_analyst and self.slot_planner),
            "analysis_ok": False,
            "analysis_text": None,
            "placeholder_used": False,
            "error": None,
            "pipeline": {},
        }
        images: List[GeneratedImage] = []

        try:
            processed_assets, product_images, reference_images, source_images, related_images, warnings = await self._prepare_assets(payload)
            analysis, keyword_plan, primary_image, source_image = await self._build_context(payload, product_images, source_images)
            provider_health = self._provider_health(keyword_plan, warnings)

            analysis_meta["analysis_ok"] = bool(analysis.visual_style or analysis.composition or analysis.lighting)
            analysis_meta["analysis_text"] = self._analysis_text(analysis)
            analysis_meta["pipeline"]["provider_health"] = provider_health.model_dump()
            analysis_meta["pipeline"]["product_analysis"] = analysis.model_dump()
            analysis_meta["pipeline"]["keyword_plan"] = keyword_plan.model_dump()

            slot_plans = []
            if payload.image_briefs:
                await self.ai_client.ensure_ready()
            for brief in payload.image_briefs:
                style_template = StyleTemplate.MINIMAL if brief.slot_name == "main_product" else payload.style_template
                slot_plan = await self.slot_planner.plan_slot(
                    project=payload.project,
                    brand=payload.brand,
                    product=payload.product,
                    brief=brief,
                    style_template=style_template,
                    analysis=analysis,
                    keyword_plan=keyword_plan,
                    primary_image=primary_image,
                    feedback=feedback,
                )
                slot_plans.append(slot_plan.model_dump())

                if brief.slot_name == "main_product":
                    if not source_image:
                        raise ValueError("Main product generation requires a valid source image.")
                    try:
                        final_image_url = await self.ai_client.generate_image(
                            slot_plan.generation_prompt,
                            size=self.settings.image_size,
                            input_images=[source_image],
                        )
                    except Exception as exc:
                        warnings.append(f"Main image AI cleanup failed; used deterministic fallback. {exc}")
                        final_image_url = await self.image_compositor.compose_main_product(
                            source_image,
                            canvas_size=(1024, 1024),
                        )
                else:
                    generated_image_url = None
                    if brief.slot_name == "lifestyle":
                        generation_images = self._select_generation_images(
                            slot_name=brief.slot_name,
                            reference_images=reference_images,
                        )
                        generated_image_url = await self.ai_client.generate_image(
                            slot_plan.generation_prompt,
                            size=self.settings.image_size,
                            input_images=generation_images or None,
                        )
                    final_image_url = await self.image_compositor.compose(
                        generated_image_url,
                        slot_plan,
                        payload.brand,
                        hero_image_url=primary_image,
                        raw_product_url=source_image,
                        related_image_urls=related_images,
                    )
                file_path = await save_image(final_image_url, self.settings.output_dir, f"{job_id}_{brief.slot_name}.png")

                images.append(
                    GeneratedImage(
                        slot_name=brief.slot_name,
                        prompt=slot_plan.generation_prompt,
                        image_url=final_image_url,
                        file_path=file_path,
                        background_removed=any(changed for _, _, changed in processed_assets),
                    )
                )

            analysis_meta["pipeline"]["slot_plans"] = slot_plans
            self.jobs.set_images(job_id, images)

            if images and self.quality_reviewer and images[0].image_url:
                qa = self._qa_from_dict(await self.quality_reviewer.review(images[0].image_url, images[0].slot_name))
                if qa:
                    analysis_meta["pipeline"]["quality_review"] = qa.model_dump()
                    if qa.score < 0.5:
                        analysis_meta["error"] = f"Quality score low ({qa.score}); issues: {qa.issues}"

            if keyword_plan.warning and not analysis_meta["error"]:
                analysis_meta["error"] = keyword_plan.warning

            self.jobs.set_status(job_id, "completed")
            return job_id, analysis_meta

        except Exception as exc:
            analysis_meta["error"] = f"Generation exception: {exc}"
            self.jobs.set_status(job_id, "failed")
            return job_id, analysis_meta

    async def generate(self, payload: ImageGenerationRequest) -> tuple[str, dict]:
        return await self._execute(payload)

    async def refine(self, payload: ImageGenerationRequest, feedback: str) -> tuple[str, dict]:
        return await self._execute(payload, feedback=feedback)

    def get_status(self, job_id: str):
        return self.jobs.get(job_id)
