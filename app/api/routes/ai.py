"""
Step 4 — Image Generation & Refinement API routes.
Generate, refine, and check status of marketplace-ready product images.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_image_generation_service, get_job_store
from app.schemas.generation import ImageGenerationRequest, GenerationResponse
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.image import GenerationStatus
from app.services.image_generation import ImageGenerationService
from app.services.job_store import InMemoryJobStore

router = APIRouter(prefix="/ai", tags=["Step 4 — Image Generation"])


@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=202,
    summary="Generate marketplace images",
    description=(
        "Submit an image generation request for one or more image slots "
        "(main_product, key_facts, lifestyle, usps, comparison, cross_selling, closing). "
        "Returns a job_id for polling via the /jobs endpoint. "
        "Each slot has anti-hallucination prompts — only user-provided text is rendered."
    ),
)
async def generate_images(
    payload: ImageGenerationRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service),
) -> GenerationResponse:
    job_id = await generator.generate(payload)
    return GenerationResponse(job_id=job_id, status="queued")


@router.get(
    "/jobs/{job_id}",
    response_model=GenerationStatus,
    summary="Check generation job status",
    description=(
        "Poll the status of an image generation or refinement job. "
        "Returns 'queued', 'processing', or 'completed' with generated image URLs."
    ),
)
async def get_job_status(
    job_id: str,
    store: InMemoryJobStore = Depends(get_job_store),
):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return GenerationStatus(job_id=job_id, status=job.status, images=job.images)


@router.post(
    "/refine",
    response_model=FeedbackResponse,
    status_code=202,
    summary="Refine a generated image",
    description=(
        "Submit refinement feedback for a previously generated image. "
        "Provide the original generation request plus free-text feedback "
        "(e.g., 'make the background brighter', 'add more contrast'). "
        "Returns a new job_id to poll for the refined image."
    ),
)
async def refine_images(
    payload: FeedbackRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service),
) -> FeedbackResponse:
    job_id = await generator.refine(payload.request, payload.feedback)
    return FeedbackResponse(job_id=job_id, status="queued")
