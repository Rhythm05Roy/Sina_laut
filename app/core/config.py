from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import HttpUrl

class Settings(BaseSettings):
    app_name: str = "Sina Laut AI"
    api_prefix: str = "/api"
    version: str = "0.1.0"

    # AI provider: Nano Banana (Gemini image)
    nano_banana_api_key: str | None = None
    # default to Imagen fast model; adjust if you have access to pro
    nano_banana_model: str = "imagen-3.0-fast"
    nano_banana_base_url: HttpUrl = "https://generativelanguage.googleapis.com/v1beta"

    image_size: str = "1024x1024"
    output_dir: str = "output"
    storage_base_url: HttpUrl | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
