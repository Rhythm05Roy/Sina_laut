from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class BrandCI(BaseModel):
    logo_url: Optional[HttpUrl] = Field(None, description="Uploaded logo location")
    primary_color: str = Field(..., pattern=r"^#?[0-9a-fA-F]{6}$", description="Hex color")
    secondary_color: str = Field(..., pattern=r"^#?[0-9a-fA-F]{6}$", description="Hex color")
    font_heading: str = Field(..., example="Inter")
    font_body: str = Field(..., example="Roboto")
