from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class StyleTemplate(str, Enum):
    """Available style templates for image generation."""
    PLAYFUL = "playful"      # Playmobil reference style - vibrant, circular badges
    MODERN = "modern"        # Clean professional - rectangular, muted
    MINIMAL = "minimal"      # Text-focused, subtle branding


class StyleConfig(BaseModel):
    """Configuration for style template selection."""
    template: StyleTemplate = Field(
        default=StyleTemplate.PLAYFUL,
        description="The visual style template to apply"
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional custom layout instructions to override defaults"
    )
