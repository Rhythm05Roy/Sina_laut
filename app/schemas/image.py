from typing import List, Optional
from pydantic import BaseModel, Field

class ImageBrief(BaseModel):
    slot_name: str = Field(..., example="main_product")
    instructions: str = Field(..., example="White background, product centered, no text")
    emphasis: List[str] = Field(default_factory=list, description="Key attributes to highlight")
    style: Optional[str] = Field(None, example="Playful, bright, kid-friendly")

class GeneratedImage(BaseModel):
    slot_name: str
    prompt: str
    image_url: str
    background_removed: bool = False
    file_path: str | None = None

class GenerationStatus(BaseModel):
    job_id: str
    status: str
    images: List[GeneratedImage] | None = None
