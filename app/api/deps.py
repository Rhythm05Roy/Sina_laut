from fastapi import Depends

from app.core.config import get_settings, Settings
from app.services.job_store import InMemoryJobStore
from app.services.image_generation import ImageGenerationService

_jobs_store = InMemoryJobStore()
_image_service: ImageGenerationService | None = None


def get_settings_dep() -> Settings:
    return get_settings()


def get_job_store() -> InMemoryJobStore:
    return _jobs_store


def get_image_generation_service(
    settings: Settings = Depends(get_settings_dep),
    store: InMemoryJobStore = Depends(get_job_store),
) -> ImageGenerationService:
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService(settings=settings, jobs=store)
    return _image_service
