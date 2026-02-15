from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import health, ai, project, brand, product

settings = get_settings()

# ── Swagger / OpenAPI configuration ──
app = FastAPI(
    title=settings.app_name,
    description=(
        "## AI-Powered Marketplace Image Generation\n\n"
        "Generate production-grade product listing images for **Amazon**, **Google Shopping**, and more.\n\n"
        "### Wizard Flow\n"
        "The API follows the same 4-step wizard as the Streamlit UI:\n\n"
        "| Step | Endpoint Group | Description |\n"
        "|------|---------------|-------------|\n"
        "| **1** | `/api/project` | Create project (name, brand, category, marketplace) |\n"
        "| **2** | `/api/brand` | Configure brand CI (logo, colors, fonts) |\n"
        "| **3** | `/api/product` | Set product info (SKU, title, USPs, keywords) |\n"
        "| **4** | `/api/ai` | Generate & refine images per slot |\n\n"
        "### Image Slots\n"
        "Each project generates up to 7 images:\n"
        "1. **Main Product** — background removal only\n"
        "2. **Key Facts** — infographic with key product facts\n"
        "3. **Lifestyle** — product in real-world setting\n"
        "4. **USP Highlight** — unique selling points with callout boxes\n"
        "5. **Comparison** — us vs others (advantages / limitations)\n"
        "6. **Cross-Selling** — related products grid\n"
        "7. **Closing** — emotional / inspirational final image\n"
    ),
    version=settings.version,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Step 1 — Project Setup",
            "description": "Create and manage image generation projects.",
        },
        {
            "name": "Step 2 — Brand CI",
            "description": "Configure brand identity: logo, colors, fonts.",
        },
        {
            "name": "Step 3 — Product Info",
            "description": "Set product details: SKU, title, description, USPs, keywords, languages.",
        },
        {
            "name": "Step 4 — Image Generation",
            "description": (
                "Generate, refine, and poll marketplace-ready product images. "
                "Supports 7 slot types with anti-hallucination prompts."
            ),
        },
        {
            "name": "system",
            "description": "Health checks and system status.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all route modules ──
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(project.router, prefix=settings.api_prefix)
app.include_router(brand.router, prefix=settings.api_prefix)
app.include_router(product.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} v{settings.version} running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
