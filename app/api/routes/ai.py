"""
Step 4 — Image Generation & Refinement API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
import base64
import mimetypes
from pathlib import Path

from app.api.deps import get_image_generation_service, get_job_store
from app.schemas.generation import ImageGenerationRequest, GenerationResponse, Asset
from app.schemas.style_template import StyleTemplate
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.image import GenerationStatus, ImageBrief
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.services.image_generation import ImageGenerationService
from app.services.job_store import InMemoryJobStore
from app.core.store import (
    projects, get_brand_by_project_id, get_product_by_project_id,
    save_generated_image_url, get_generated_image_url,
    save_asset_url, get_asset_url
)
from app.services.slots import build_followup_suggestions
from app.schemas.step4 import (
    Image1Request, Image2Request, Image3Request, Image4Request,
    Image5Request, Image6Request, Image7Request,
    Image1RefineRequest, Image2RefineRequest, Image3RefineRequest, 
    Image4RefineRequest, Image5RefineRequest, Image6RefineRequest, 
    Image7RefineRequest
)

router = APIRouter(prefix="/step4", tags=["Step 4 — Image Generation"])


# --- Helpers ---
def build_base_request(project_id: str) -> tuple[ProjectSetup, BrandCI, ProductInfo]:
    proj_data = projects.get(project_id)
    if not proj_data:
        raise HTTPException(status_code=404, detail="Project not found. Complete Step 1.")
    
    brand_data = get_brand_by_project_id(project_id)
    if not brand_data:
        raise HTTPException(status_code=404, detail="Brand CI not found. Complete Step 2.")
    
    prod_data = get_product_by_project_id(project_id)
    if not prod_data:
        raise HTTPException(status_code=404, detail="Product info not found. Complete Step 3.")
        
    return ProjectSetup(**proj_data), BrandCI(**brand_data), ProductInfo(**prod_data)


def normalize_image_url(maybe_path: str) -> str:
    """
    Accepts data URL, http(s) URL, or local file path.
    If it's a local file path, read and convert to data URL.
    """
    if not maybe_path:
        return maybe_path
    lower = maybe_path.lower()
    if lower.startswith("data:") or lower.startswith("http://") or lower.startswith("https://"):
        return maybe_path
    path = Path(maybe_path)
    if path.exists() and path.is_file():
        mime, _ = mimetypes.guess_type(path.name)
        mime = mime or "application/octet-stream"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    return maybe_path


async def _run_generation(
    generator: ImageGenerationService, 
    project_id: str, 
    slot_name: str, 
    instructions: str, 
    emphasis: List[str] = [],
    assets: List[Asset] = [],
    style_template: str = "playful",
    remove_background: bool = True
) -> GenerationResponse:
    
    project, brand, product = build_base_request(project_id)
    
    # Convert string to StyleTemplate enum
    try:
        style_enum = StyleTemplate(style_template)
    except ValueError:
        style_enum = StyleTemplate.PLAYFUL
    
    brief = ImageBrief(
        slot_name=slot_name,
        instructions=instructions,
        emphasis=emphasis,
        style=style_template
    )
    
    full_req = ImageGenerationRequest(
        project=project,
        brand=brand,
        product=product,
        assets=assets,
        image_briefs=[brief],
        remove_background=remove_background,
        style_template=style_enum
    )
    
    job_id, analysis_meta = await generator.generate(full_req)
    
    # Check if done immediately (blocking implementation)
    job = generator.get_status(job_id)
    if job and job.status == "completed" and job.images:
        img_url = job.images[0].image_url
        if img_url:
            save_generated_image_url(project_id, slot_name, img_url)

    return GenerationResponse(
        job_id=job_id,
        status="queued" if not analysis_meta.get("placeholder_used") else "failed",
        analysis_used=analysis_meta.get("analysis_used"),
        analysis_ok=analysis_meta.get("analysis_ok"),
        analysis_text=analysis_meta.get("analysis_text"),
        placeholder_used=analysis_meta.get("placeholder_used"),
        error=analysis_meta.get("error"),
    )


async def _run_refinement(
    generator: ImageGenerationService,
    project_id: str,
    slot_name: str,
    instructions: str,
    feedback: str,
    emphasis: List[str] = [],
    assets: List[Asset] = [],
    style_template: str = "playful",
    remove_background: bool = False
) -> GenerationResponse:

    project, brand, product = build_base_request(project_id)

    # Convert string to StyleTemplate enum
    try:
        style_enum = StyleTemplate(style_template)
    except ValueError:
        style_enum = StyleTemplate.PLAYFUL

    # Context: Previously generated image for this slot
    prev_img = get_generated_image_url(project_id, slot_name)
    if prev_img:
        # Add as asset to be refined
        assets.append(Asset(type="product_photo", url=prev_img))

    brief = ImageBrief(
        slot_name=slot_name,
        instructions=instructions,
        emphasis=emphasis,
        style=style_template
    )

    full_req = ImageGenerationRequest(
        project=project,
        brand=brand,
        product=product,
        assets=assets,
        image_briefs=[brief],
        remove_background=remove_background,
        style_template=style_enum
    )

    job_id, analysis_meta = await generator.refine(full_req, feedback)

    # Check if done immediately
    job = generator.get_status(job_id)
    if job and job.status == "completed" and job.images:
        img_url = job.images[0].image_url
        if img_url:
            save_generated_image_url(project_id, slot_name, img_url)

    return GenerationResponse(
        job_id=job_id,
        status="queued" if not analysis_meta.get("placeholder_used") else "failed",
        analysis_used=analysis_meta.get("analysis_used"),
        analysis_ok=analysis_meta.get("analysis_ok"),
        analysis_text=analysis_meta.get("analysis_text"),
        placeholder_used=analysis_meta.get("placeholder_used"),
        error=analysis_meta.get("error"),
    )


# --- GENERATION ENDPOINTS ---

# 1. Main Product
@router.post("/generate/main-product", response_model=GenerationResponse, summary="1. Generate Main Product")
async def generate_image1(
    payload: Image1Request = Body(
        ...,
        examples={
            "default": {
                "summary": "Main product image (white background)",
                "value": {
                    "project_id": "PROJECT_ID_FROM_STEP1",
                    "style_template": "minimal",
                    "image_url": "data:image/png;base64,REPLACE_WITH_REAL_BASE64_IMAGE"
                }
            },
            "local_file": {
                "summary": "Local file path (auto-converted to data URL)",
                "value": {
                    "project_id": "PROJECT_ID_FROM_STEP1",
                    "style_template": "minimal",
                    "image_url": "C:\\\\Users\\\\YourName\\\\Pictures\\\\product.png"
                }
            }
        }
    ),
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    normalized = normalize_image_url(payload.image_url)
    save_asset_url(payload.project_id, "main_raw", normalized)
    assets = [Asset(type="product_photo", url=normalized)]
    resp = await _run_generation(
        generator, payload.project_id, "main_product",
        instructions="Create a marketplace-ready product image. Pure white background. Product centered. No text.",
        assets=assets,
        style_template=payload.style_template,
        remove_background=True
    )
    # Auto-suggest prompts for downstream slots using current context
    try:
        project, brand, product = build_base_request(payload.project_id)
        resp.suggested_prompts = build_followup_suggestions(
            project, brand, product, payload.image_url, payload.style_template
        )
    except Exception:
        # Non-fatal: suggestions are optional
        resp.suggested_prompts = None
    return resp

# 2. Key Facts
@router.post("/generate/key-facts", response_model=GenerationResponse, summary="2. Generate Key Facts")
async def generate_image2(
    payload: Image2Request,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product") or get_asset_url(payload.project_id, "main_raw")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    facts_text = "; ".join(payload.key_facts)
    return await _run_generation(
        generator, payload.project_id, "key_facts",
        instructions=f"Create a product infographic. Background: {payload.background_style}. Logo: {payload.logo_position}. Facts: {facts_text}.",
        emphasis=payload.key_facts,
        assets=assets,
        style_template=payload.style_template,
        remove_background=False
    )

# 3. Lifestyle
@router.post("/generate/lifestyle", response_model=GenerationResponse, summary="3. Generate Lifestyle")
async def generate_image3(
    payload: Image3Request,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))
    if payload.ref_image_url:
        assets.append(Asset(type="product_photo", url=payload.ref_image_url))

    return await _run_generation(
        generator, payload.project_id, "lifestyle",
        instructions=f"Lifestyle scene: {payload.scenario}",
        assets=assets,
        style_template=payload.style_template,
        remove_background=False
    )

# 4. USP Highlight
@router.post("/generate/usps", response_model=GenerationResponse, summary="4. Generate USP Highlight")
async def generate_image4(
    payload: Image4Request,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    return await _run_generation(
        generator, payload.project_id, "usps",
        instructions=f"USP Highlights: {'; '.join(payload.usps)}",
        emphasis=payload.usps,
        assets=assets,
        style_template=payload.style_template,
        remove_background=False
    )

# 5. Comparison
@router.post("/generate/comparison", response_model=GenerationResponse, summary="5. Generate Comparison")
async def generate_image5(
    payload: Image5Request,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    all_items = [f"ADV:{a}" for a in payload.advantages] + [f"LIM:{l}" for l in payload.limitations]
    return await _run_generation(
        generator, payload.project_id, "comparison",
        instructions="Comparison infographic. Left: Advantages (Green). Right: Limitations (Red).",
        emphasis=all_items,
        assets=assets,
        style_template=payload.style_template,
        remove_background=False
    )

# 6. Cross-Selling
@router.post("/generate/cross-selling", response_model=GenerationResponse, summary="6. Generate Cross-Selling")
async def generate_image6(
    payload: Image6Request,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    return await _run_generation(
        generator, payload.project_id, "cross_selling",
        instructions=f"Cross-selling grid: {', '.join(payload.product_names)}",
        emphasis=payload.product_names,
        assets=assets,
        style_template=payload.style_template,
        remove_background=False
    )

# 7. Closing
@router.post("/generate/closing", response_model=GenerationResponse, summary="7. Generate Closing")
async def generate_image7(
    payload: Image7Request,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    emphasis = [payload.headline] if payload.headline else []
    return await _run_generation(
        generator, payload.project_id, "closing",
        instructions=f"Closing image. Direction: {payload.direction}. Headline: {payload.headline or 'None'}",
        emphasis=emphasis,
        assets=assets,
        style_template=payload.style_template,
        remove_background=False
    )


# --- REFINEMENT ENDPOINTS ---

@router.post("/refine/main-product", response_model=GenerationResponse, summary="Refine Main Product")
async def refine_image1(
    payload: Image1RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    normalized = normalize_image_url(payload.image_url)
    assets = [Asset(type="product_photo", url=normalized)]
    return await _run_refinement(
        generator, payload.project_id, "main_product",
        instructions="Create a marketplace-ready product image. Pure white background. Product centered. No text.",
        feedback=payload.feedback,
        assets=assets,
        style_template=payload.style_template,
        remove_background=True
    )

@router.post("/refine/key-facts", response_model=GenerationResponse, summary="Refine Key Facts")
async def refine_image2(
    payload: Image2RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    # Context logic same as generation (plus the generated image fetched by _run_refinement)
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    facts_text = "; ".join(payload.key_facts)
    return await _run_refinement(
        generator, payload.project_id, "key_facts",
        instructions=f"Create a product infographic. Background: {payload.background_style}. Logo: {payload.logo_position}. Facts: {facts_text}.",
        feedback=payload.feedback,
        emphasis=payload.key_facts,
        assets=assets,
        style_template=payload.style_template
    )

@router.post("/refine/lifestyle", response_model=GenerationResponse, summary="Refine Lifestyle")
async def refine_image3(
    payload: Image3RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))
    if payload.ref_image_url:
        assets.append(Asset(type="product_photo", url=payload.ref_image_url))

    return await _run_refinement(
        generator, payload.project_id, "lifestyle",
        instructions=f"Lifestyle scene: {payload.scenario}",
        feedback=payload.feedback,
        assets=assets,
        style_template=payload.style_template
    )

@router.post("/refine/usps", response_model=GenerationResponse, summary="Refine USP Highlight")
async def refine_image4(
    payload: Image4RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    return await _run_refinement(
        generator, payload.project_id, "usps",
        instructions=f"USP Highlights: {'; '.join(payload.usps)}",
        feedback=payload.feedback,
        emphasis=payload.usps,
        assets=assets,
        style_template=payload.style_template
    )

@router.post("/refine/comparison", response_model=GenerationResponse, summary="Refine Comparison")
async def refine_image5(
    payload: Image5RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))
    
    all_items = [f"ADV:{a}" for a in payload.advantages] + [f"LIM:{l}" for l in payload.limitations]
    return await _run_refinement(
        generator, payload.project_id, "comparison",
        instructions="Comparison infographic. Left: Advantages (Green). Right: Limitations (Red).",
        feedback=payload.feedback,
        emphasis=all_items,
        assets=assets,
        style_template=payload.style_template
    )

@router.post("/refine/cross-selling", response_model=GenerationResponse, summary="Refine Cross-Selling")
async def refine_image6(
    payload: Image6RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    return await _run_refinement(
        generator, payload.project_id, "cross_selling",
        instructions=f"Cross-selling grid: {', '.join(payload.product_names)}",
        feedback=payload.feedback,
        emphasis=payload.product_names,
        assets=assets,
        style_template=payload.style_template
    )

@router.post("/refine/closing", response_model=GenerationResponse, summary="Refine Closing")
async def refine_image7(
    payload: Image7RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    assets = []
    img1 = get_generated_image_url(payload.project_id, "main_product")
    if img1: assets.append(Asset(type="product_photo", url=img1))

    emphasis = [payload.headline] if payload.headline else []
    return await _run_refinement(
        generator, payload.project_id, "closing",
        instructions=f"Closing image. Direction: {payload.direction}. Headline: {payload.headline or 'None'}",
        feedback=payload.feedback,
        emphasis=emphasis,
        assets=assets,
        style_template=payload.style_template
    )


@router.get("/jobs/{job_id}", response_model=GenerationStatus, summary="Check Job Status")
async def get_job_status(job_id: str, store: InMemoryJobStore = Depends(get_job_store)):
    job = store.get(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    return GenerationStatus(job_id=job_id, status=job.status, images=job.images)
