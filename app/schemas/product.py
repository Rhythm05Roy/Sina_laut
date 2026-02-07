from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ProductInfo(BaseModel):
    sku: str = Field(..., example="SKU-12345")
    title: str = Field(..., example="Premium Wireless Headphones")
    short_description: str = Field(..., example="Noise-cancelling over-ear headphones with 40h battery")
    usps: List[str] = Field(default_factory=list, description="Unique selling points")
    keywords: Dict[str, List[str]] = Field(default_factory=dict, description="Marketplace specific keywords")
    languages: List[str] = Field(default_factory=lambda: ["en"], description="Selected languages")

