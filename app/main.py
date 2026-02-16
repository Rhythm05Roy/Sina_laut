from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import health, ai, project, brand, product

settings = get_settings()

# ── Swagger / OpenAPI configuration ──
app = FastAPI(
    title=settings.app_name,
    description=(
        "## AI-Powered Marketplace Image Generation API\n\n"
        "Generate production-grade product listing images following a stateful, step-by-step wizard flow.\n\n"
        "### Step-by-Step API Flow\n\n"
        "The API mirrors the 4-step wizard UI:\n\n"
        "| Step | Route Prefix | Action | Output |\n"
        "|------|--------------|--------|--------|\n"
        "| **1** | `/api/step1/project` | Create Project | `project_id` |\n"
        "| **2** | `/api/step2/brand` | Save Brand CI | linked to `project_id` |\n"
        "| **3** | `/api/step3/product` | Save Product Info | linked to `project_id` |\n"
        "| **4** | `/api/step4/generate` | Generate Images | `job_id` |\n\n"
        "### Usage\n"
        "1. Start by creating a project in **Step 1** to get a `id`.\n"
        "2. Use that `id` to configure Brand (Step 2) and Product (Step 3).\n"
        "3. Finally, call Step 4 generation endpoints using the same `id` to produce images based on the saved context.\n"
    ),
    version=settings.version,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Step 1 — Project Setup",
            "description": "Create a new image generation project.",
        },
        {
            "name": "Step 2 — Brand CI",
            "description": "Configure brand identity (logo, colors, fonts).",
        },
        {
            "name": "Step 3 — Product Info",
            "description": "Set product details (SKU, title, USPs).",
        },
        {
            "name": "Step 4 — Image Generation",
            "description": "Generate images statefully using project context.",
        },
        {
            "name": "system",
            "description": "Health checks.",
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
# Note: Prefixes inside routers handle the /stepX part. api_prefix handles /api.
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
        "steps": [
            "/api/step1/project",
            "/api/step2/brand",
            "/api/step3/product",
            "/api/step4/generate",
        ]
    }
