# Sina Laut AI API

FastAPI backend for AI-assisted product image generation. Mirrors the UI flow in the provided mockups: project setup ? brand CI ? product info ? image brief selection ? AI image set generation.

## Project structure
- `app/main.py` – FastAPI app + router wiring.
- `app/core/config.py` – settings via environment/.env.
- `app/api/routes/` – HTTP endpoints (`health`, `ai`).
- `app/api/deps.py` – shared dependency wiring and singletons.
- `app/schemas/` – Pydantic models for project, brand, product, briefs, and job status.
- `app/services/` – AI client wrapper, prompt builder, keyword crawler stub, background removal stub, job store, and orchestration service.
- `.env.example` – environment variable template.

## Run locally
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env  # set NANO_BANANA_API_KEY if available
uvicorn app.main:app --reload --port 8000
```
Open docs: http://localhost:8000/api/docs

## Core endpoints
- `GET /api/health` – health check.
- `POST /api/ai/generate` – start an image-generation job (returns `job_id`).
- `GET /api/ai/jobs/{job_id}` – poll job status + generated image URLs.

### Example request body
```json
{
  "project": {
    "project_name": "Playmobil Launch",
    "brand_name": "Playmobil",
    "product_category": "Toys",
    "target_marketplaces": ["amazon"]
  },
  "brand": {
    "logo_url": "https://example.com/logo.png",
    "primary_color": "#6366f1",
    "secondary_color": "#8b5cf6",
    "font_heading": "Inter",
    "font_body": "Roboto"
  },
  "product": {
    "sku": "SKU-12345",
    "title": "Cat Cafe Playset",
    "short_description": "Playset with figures and cafe props",
    "usps": ["72 pieces", "Great for small hands"],
    "keywords": {"amazon": ["cat cafe", "playset"]},
    "languages": ["en"]
  },
  "assets": [{"type": "product_photo", "url": "https://example.com/photo.jpg"}],
  "image_briefs": [
    {
      "slot_name": "main_product",
      "instructions": "White background, product centered, Amazon compliant",
      "emphasis": ["hero product", "brand logo"],
      "style": "Bright, kid friendly"
    }
  ],
  "remove_background": true
}
```

## Notes
- AI client targets Nano Banana (Gemini image API). Set `NANO_BANANA_API_KEY`; without it the service returns placeholder image URLs for development.
- Keyword crawler and background removal are stubs with clear integration points for production tools.
- Image prompts blend project, brand CI (colors/fonts), product info, and per-slot briefs to stay aligned with the UI flow and sample storyboard.
