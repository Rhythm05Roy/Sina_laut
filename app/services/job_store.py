from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app.schemas.image import GeneratedImage

@dataclass
class JobRecord:
    status: str
    images: list[GeneratedImage] | None = field(default=None)

class InMemoryJobStore:
    def __init__(self) -> None:
        self._store: Dict[str, JobRecord] = {}

    def create(self, job_id: str, status: str = "queued") -> None:
        self._store[job_id] = JobRecord(status=status)

    def set_status(self, job_id: str, status: str) -> None:
        if job_id in self._store:
            self._store[job_id].status = status

    def set_images(self, job_id: str, images: list[GeneratedImage]) -> None:
        if job_id in self._store:
            self._store[job_id].images = images

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self._store.get(job_id)
