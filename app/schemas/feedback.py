from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from app.schemas.generation import ImageGenerationRequest

class FeedbackRequest(BaseModel):
    feedback: str = Field(..., description="Structured refinement, e.g. 'more premium look'")
    request: ImageGenerationRequest

class FeedbackResponse(BaseModel):
    job_id: str
    status: str
