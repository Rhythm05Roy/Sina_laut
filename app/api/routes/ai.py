from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_image_generation_service, get_job_store
from app.schemas.generation import ImageGenerationRequest, GenerationResponse
from app.schemas.image import GenerationStatus
from app.services.image_generation import ImageGenerationService
from app.services.job_store import InMemoryJobStore

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate", response_model=GenerationResponse, status_code=202)
async def generate_images(
    payload: ImageGenerationRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service),
) -> GenerationResponse:
    job_id = await generator.generate(payload)
    return GenerationResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=GenerationStatus)
async def get_job_status(
    job_id: str,
    store: InMemoryJobStore = Depends(get_job_store),
):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return GenerationStatus(job_id=job_id, status=job.status, images=job.images)
