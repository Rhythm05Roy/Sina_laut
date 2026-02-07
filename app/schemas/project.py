from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from typing import List

class Marketplace(str, Enum):
    amazon = "amazon"
    google = "google"

class ProjectSetup(BaseModel):
    project_name: str = Field(..., example="Summer Collection 2024")
    brand_name: str = Field(..., example="EcoStyle")
    product_category: str = Field(..., example="Toys & Games")
    target_marketplaces: List[Marketplace] = Field(..., example=["amazon", "google"])

class ProjectResponse(ProjectSetup):
    id: str
