from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import HttpUrl
from typing import Optional


class Settings(BaseSettings):
    """Application settings — all API keys are loaded from .env for easy backend configuration."""

    app_name: str = "Sina Laut AI"
    app_description: str = (
        "AI-powered marketplace image generation service. "
        "Generate production-grade product listing images for Amazon, Google Shopping, and more."
    )
    api_prefix: str = "/api"
    version: str = "0.2.0"

    # ── Primary AI Provider: Google Gemini ──
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash-image"
    gemini_base_url: HttpUrl = "https://generativelanguage.googleapis.com/v1beta"

    # ── Legacy aliases (backwards compatible with existing .env files) ──
    nano_banana_api_key: Optional[str] = None
    nano_banana_model: str = "gemini-2.5-flash-image"
    nano_banana_base_url: HttpUrl = "https://generativelanguage.googleapis.com/v1beta"

    # ── Future providers (ready for backend team to plug in) ──
    openai_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None
    replicate_api_key: Optional[str] = None
    # DataForSEO credentials (basic auth)
    dataforseo_login: Optional[str] = None
    dataforseo_password: Optional[str] = None

    # ── Image output settings ──
    image_size: str = "1024x1024"
    output_dir: str = "output"
    storage_base_url: Optional[HttpUrl] = None

    @property
    def active_api_key(self) -> Optional[str]:
        """Returns the active API key, preferring gemini_api_key over legacy alias."""
        return self.gemini_api_key or self.nano_banana_api_key

    @property
    def active_model(self) -> str:
        """Returns the active model name."""
        if self.gemini_api_key:
            return self.gemini_model
        return self.nano_banana_model

    @property
    def active_base_url(self) -> str:
        """Returns the active base URL."""
        if self.gemini_api_key:
            return str(self.gemini_base_url)
        return str(self.nano_banana_base_url)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
