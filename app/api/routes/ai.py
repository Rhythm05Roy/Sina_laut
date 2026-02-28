"""
Step 4 — Image Generation & Refinement API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
import base64
import mimetypes
from pathlib import Path
from uuid import uuid4

from app.api.deps import get_image_generation_service, get_job_store
from app.schemas.generation import ImageGenerationRequest, GenerationResponse, Asset
from app.schemas.style_template import StyleTemplate
from app.schemas.image import GenerationStatus, ImageBrief
from app.schemas.project import ProjectSetup
from app.schemas.brand import BrandCI
from app.schemas.product import ProductInfo
from app.services.image_generation import ImageGenerationService
from app.services.job_store import InMemoryJobStore
from app.core.store import (
    projects, brands, products, get_brand_by_project_id, get_product_by_project_id,
    save_generated_image_url, get_generated_image_url,
    save_asset_url, get_asset_url,
    save_generation_context, get_project_id_by_context, get_latest_context_id,
    bind_job_to_context
)
from app.services.slots import build_followup_suggestions
from app.schemas.step4 import (
    Image1Request, Image2Request, Image3Request, Image4Request,
    Image5Request, Image6Request, Image7Request,
    Image1RefineRequest, Image2RefineRequest, Image3RefineRequest, 
    Image4RefineRequest, Image5RefineRequest, Image6RefineRequest,
    Image7RefineRequest, ExternalProjectPayload
)

router = APIRouter(prefix="/step4", tags=["Step 4 — Image Generation"])


# --- Helpers ---
def _normalize_marketplace(value: Optional[str]) -> str:
    raw = (value or "amazon").strip().lower()
    if raw in {"amazon", "amz"}:
        return "amazon"
    if raw in {"google", "google_shopping"}:
        return "google"
    return "amazon"


def _upsert_project_from_external(project: ExternalProjectPayload) -> str:
    project_id = project.id
    marketplace = _normalize_marketplace(project.targetMarketplace)
    existing = projects.get(project_id, {})
    projects[project_id] = {
        "id": project_id,
        "project_name": project.name or existing.get("project_name") or "Imported Project",
        "brand_name": project.brandName or existing.get("brand_name") or "Imported Brand",
        "product_category": project.productCategory or existing.get("product_category") or "General",
        "target_marketplaces": [marketplace],
    }
    if project.mainImage:
        save_asset_url(project_id, "main_raw", normalize_image_url(project.mainImage))

    existing_brand = get_brand_by_project_id(project_id)
    if not existing_brand:
        brand_id = str(uuid4())
        brands[brand_id] = {
            "id": brand_id,
            "project_id": project_id,
            "logo_url": None,
            "primary_color": "#111111",
            "secondary_color": "#333333",
            "font_heading": project.brandFontHeading or "Inter",
            "font_body": project.brandFontSubheading or "Roboto",
        }

    existing_product = get_product_by_project_id(project_id)
    if not existing_product:
        product_id = str(uuid4())
        products[product_id] = {
            "id": product_id,
            "project_id": project_id,
            "sku": project.sku or f"SKU-{project_id[:8]}",
            "title": project.name or (project.productCategory or "Product"),
            "short_description": project.shortDescription or "Imported product context",
            "usps": [],
            "keywords": {"primary": [], "secondary": []},
            "languages": ["en"],
        }

    return project_id


def _resolve_project_and_context(payload) -> tuple[str, str]:
    project_id: Optional[str] = None
    payload_context_id: Optional[str] = getattr(payload, "context_id", None)
    if getattr(payload, "project", None):
        project_id = _upsert_project_from_external(payload.project)
    elif getattr(payload, "project_id", None):
        project_id = payload.project_id
    elif payload_context_id:
        project_id = get_project_id_by_context(payload_context_id)
    else:
        latest_context = get_latest_context_id()
        if latest_context:
            project_id = get_project_id_by_context(latest_context)
            payload_context_id = latest_context

    if not project_id:
        raise HTTPException(
            status_code=400,
            detail="Missing project context. Send project_id, context_id, or project payload."
        )
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project context not found.")

    context_id = payload_context_id or project_id
    save_generation_context(context_id, project_id)
    return project_id, context_id


def build_base_request(project_id: str) -> tuple[ProjectSetup, BrandCI, ProductInfo]:
    proj_data = projects.get(project_id)
    if not proj_data:
        raise HTTPException(status_code=404, detail="Project not found. Complete Step 1.")

    brand_data = get_brand_by_project_id(project_id)
    if not brand_data:
        brand_id = str(uuid4())
        brands[brand_id] = {
            "id": brand_id,
            "project_id": project_id,
            "logo_url": None,
            "primary_color": "#111111",
            "secondary_color": "#333333",
            "font_heading": "Inter",
            "font_body": "Roboto",
        }
        brand_data = brands[brand_id]

    prod_data = get_product_by_project_id(project_id)
    if not prod_data:
        product_id = str(uuid4())
        products[product_id] = {
            "id": product_id,
            "project_id": project_id,
            "sku": f"SKU-{project_id[:8]}",
            "title": proj_data.get("project_name", "Product"),
            "short_description": "Autogenerated product context",
            "usps": [],
            "keywords": {"primary": [], "secondary": []},
            "languages": ["en"],
        }
        prod_data = products[product_id]

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


def _extract_image_parts(image_url: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not image_url:
        return None, None
    if image_url.startswith("data:") and "," in image_url:
        header, b64 = image_url.split(",", 1)
        mime = header.replace("data:", "").split(";")[0]
        return mime, b64
    mime, _ = mimetypes.guess_type(image_url)
    return mime, None


def _to_generation_response(
    *,
    job_id: str,
    status: str,
    context_id: str,
    slot_name: str,
    analysis_meta: dict,
    generator: ImageGenerationService,
    refine_prompt: Optional[str] = None,
) -> GenerationResponse:
    job = generator.get_status(job_id)
    first_image = job.images[0] if job and job.images else None
    image_url = first_image.image_url if first_image else None
    mime, b64 = _extract_image_parts(image_url)
    file_name = None
    prompt = None
    if first_image:
        file_name = Path(first_image.file_path).name if first_image.file_path else f"{job_id}_{slot_name}.png"
        prompt = first_image.prompt

    return GenerationResponse(
        job_id=job_id,
        status=status,
        context_id=context_id,
        jobId=job_id,
        contextId=context_id,
        imageUrl=image_url,
        imageBuffer=b64,
        imageMimeType=mime,
        imageFileName=file_name,
        prompt=prompt,
        refinePrompt=refine_prompt,
        rawResponse=analysis_meta.get("pipeline"),
        analysis_used=analysis_meta.get("analysis_used"),
        analysis_ok=analysis_meta.get("analysis_ok"),
        analysis_text=analysis_meta.get("analysis_text"),
        placeholder_used=analysis_meta.get("placeholder_used"),
        error=analysis_meta.get("error"),
    )


async def _run_generation(
    generator: ImageGenerationService, 
    project_id: str,
    context_id: str,
    slot_name: str, 
    instructions: str, 
    emphasis: Optional[List[str]] = None,
    assets: Optional[List[Asset]] = None,
    style_template: str = "playful",
    remove_background: bool = True
) -> GenerationResponse:

    project, brand, product = build_base_request(project_id)
    assets = assets or []
    emphasis = emphasis or []

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
    bind_job_to_context(job_id, context_id)
    save_generation_context(context_id, project_id)

    job = generator.get_status(job_id)
    job_status = job.status if job else "queued"
    if job_status == "completed" and job and job.images:
        img_url = job.images[0].image_url
        if img_url:
            save_generated_image_url(project_id, slot_name, img_url)

    return _to_generation_response(
        job_id=job_id,
        status=job_status,
        context_id=context_id,
        slot_name=slot_name,
        analysis_meta=analysis_meta,
        generator=generator,
    )


async def _run_refinement(
    generator: ImageGenerationService,
    project_id: str,
    context_id: str,
    slot_name: str,
    instructions: str,
    feedback: str,
    emphasis: Optional[List[str]] = None,
    assets: Optional[List[Asset]] = None,
    style_template: str = "playful",
    remove_background: bool = False
) -> GenerationResponse:

    project, brand, product = build_base_request(project_id)
    assets = assets or []
    emphasis = emphasis or []

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
    bind_job_to_context(job_id, context_id)
    save_generation_context(context_id, project_id)

    job = generator.get_status(job_id)
    job_status = job.status if job else "queued"
    if job_status == "completed" and job and job.images:
        img_url = job.images[0].image_url
        if img_url:
            save_generated_image_url(project_id, slot_name, img_url)

    return _to_generation_response(
        job_id=job_id,
        status=job_status,
        context_id=context_id,
        slot_name=slot_name,
        analysis_meta=analysis_meta,
        generator=generator,
        refine_prompt=feedback,
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
    project_id, context_id = _resolve_project_and_context(payload)
    image_source = payload.image_url or (payload.project.mainImage if payload.project else None) or get_asset_url(project_id, "main_raw")
    if not image_source:
        raise HTTPException(
            status_code=400,
            detail="Main product image missing. Provide image_url or project.mainImage."
        )

    normalized = normalize_image_url(image_source)
    save_asset_url(project_id, "main_raw", normalized)
    assets = [Asset(type="product_photo", url=normalized)]
    resp = await _run_generation(
        generator, project_id, context_id, "main_product",
        instructions="Create a marketplace-ready product image. Pure white background. Product centered. No text.",
        assets=assets,
        style_template=payload.style_template,
        remove_background=True
    )
    # Auto-suggest prompts for downstream slots using current context
    try:
        project, brand, product = build_base_request(project_id)
        resp.suggested_prompts = build_followup_suggestions(
            project, brand, product, normalized, payload.style_template
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product") or get_asset_url(project_id, "main_raw")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    facts_text = "; ".join(payload.key_facts)
    return await _run_generation(
        generator, project_id, context_id, "key_facts",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))
    if payload.ref_image_url:
        assets.append(Asset(type="product_photo", url=normalize_image_url(payload.ref_image_url)))

    return await _run_generation(
        generator, project_id, context_id, "lifestyle",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    return await _run_generation(
        generator, project_id, context_id, "usps",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    all_items = [f"ADV:{a}" for a in payload.advantages] + [f"LIM:{l}" for l in payload.limitations]
    return await _run_generation(
        generator, project_id, context_id, "comparison",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    return await _run_generation(
        generator, project_id, context_id, "cross_selling",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    emphasis = [payload.headline] if payload.headline else []
    return await _run_generation(
        generator, project_id, context_id, "closing",
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
    project_id, context_id = _resolve_project_and_context(payload)
    image_source = payload.image_url or get_generated_image_url(project_id, "main_product") or get_asset_url(project_id, "main_raw")
    if not image_source:
        raise HTTPException(status_code=400, detail="No source image available for main-product refinement.")
    normalized = normalize_image_url(image_source)
    assets = [Asset(type="product_photo", url=normalized)]
    return await _run_refinement(
        generator, project_id, context_id, "main_product",
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
    project_id, context_id = _resolve_project_and_context(payload)
    # Context logic same as generation (plus the generated image fetched by _run_refinement)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    facts_text = "; ".join(payload.key_facts)
    return await _run_refinement(
        generator, project_id, context_id, "key_facts",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))
    if payload.ref_image_url:
        assets.append(Asset(type="product_photo", url=normalize_image_url(payload.ref_image_url)))

    return await _run_refinement(
        generator, project_id, context_id, "lifestyle",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    return await _run_refinement(
        generator, project_id, context_id, "usps",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))
    
    all_items = [f"ADV:{a}" for a in payload.advantages] + [f"LIM:{l}" for l in payload.limitations]
    return await _run_refinement(
        generator, project_id, context_id, "comparison",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    return await _run_refinement(
        generator, project_id, context_id, "cross_selling",
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
    project_id, context_id = _resolve_project_and_context(payload)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    emphasis = [payload.headline] if payload.headline else []
    return await _run_refinement(
        generator, project_id, context_id, "closing",
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
