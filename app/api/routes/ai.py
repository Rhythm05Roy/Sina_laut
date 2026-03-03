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
    bind_job_to_context, get_context_id_by_job,
    save_project_slot_defaults, get_project_slot_defaults
)
from app.services.slots import build_followup_suggestions
from app.schemas.step4 import (
    Image1Request,
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
    extra = getattr(project, "__pydantic_extra__", {}) or {}
    raw_id = extra.get("id")
    project_id = str(raw_id).strip() if raw_id else f"ext-{uuid4()}"
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
    extra = getattr(payload, "__pydantic_extra__", {}) or {}
    project_id: Optional[str] = None
    payload_job_id: Optional[str] = getattr(payload, "job_id", None) or extra.get("job_id")
    payload_context_id: Optional[str] = getattr(payload, "context_id", None) or extra.get("context_id")
    if payload_job_id:
        payload_context_id = get_context_id_by_job(payload_job_id)
        if not payload_context_id:
            raise HTTPException(
                status_code=404,
                detail=f"Context for job_id '{payload_job_id}' not found. Generate first, then refine."
            )
        project_id = get_project_id_by_context(payload_context_id)
    if getattr(payload, "project", None):
        project_id = _upsert_project_from_external(payload.project)
    elif getattr(payload, "project_id", None):
        project_id = payload.project_id
    elif extra.get("project_id"):
        project_id = extra.get("project_id")
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
            detail="Missing project context. Send project payload to main-product first."
        )
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project context not found.")

    context_id = payload_context_id or project_id
    save_generation_context(context_id, project_id)
    return project_id, context_id


def _resolve_latest_project_and_context() -> tuple[str, str]:
    latest_context = get_latest_context_id()
    if not latest_context:
        raise HTTPException(
            status_code=400,
            detail="No active generation context found. Call /generate/main-product first."
        )
    project_id = get_project_id_by_context(latest_context)
    if not project_id or project_id not in projects:
        raise HTTPException(status_code=404, detail="Project context not found.")
    save_generation_context(latest_context, project_id)
    return project_id, latest_context


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


def _save_defaults_from_project_payload(project_id: str, project_payload: ExternalProjectPayload):
    gen_map = {
        "key_facts": getattr(project_payload, "image2", None),
        "lifestyle": getattr(project_payload, "image3", None),
        "usps": getattr(project_payload, "image4", None),
        "comparison": getattr(project_payload, "image5", None),
        "cross_selling": getattr(project_payload, "image6", None),
        "closing": getattr(project_payload, "image7", None),
    }
    ref_map = {
        "main_product": getattr(project_payload, "refine_image1", None),
        "key_facts": getattr(project_payload, "refine_image2", None),
        "lifestyle": getattr(project_payload, "refine_image3", None),
        "usps": getattr(project_payload, "refine_image4", None),
        "comparison": getattr(project_payload, "refine_image5", None),
        "cross_selling": getattr(project_payload, "refine_image6", None),
        "closing": getattr(project_payload, "refine_image7", None),
    }
    for slot_name, cfg in gen_map.items():
        if cfg:
            save_project_slot_defaults(project_id, "generate", slot_name, cfg.model_dump(exclude_none=True))
    for slot_name, cfg in ref_map.items():
        if cfg:
            save_project_slot_defaults(project_id, "refine", slot_name, cfg.model_dump(exclude_none=True))


def _strip_none(payload_dict: dict) -> dict:
    return {
        k: v for k, v in payload_dict.items()
        if v is not None and (not isinstance(v, list) or len(v) > 0)
    }


def _merge_slot_inputs(project_id: str, stage: str, slot_name: str, payload_dict: dict) -> dict:
    merged = {}
    if stage == "refine":
        merged.update(get_project_slot_defaults(project_id, "generate", slot_name))
    merged.update(get_project_slot_defaults(project_id, stage, slot_name))
    merged.update(_strip_none(payload_dict))
    return merged


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
    slot_name: str,
    analysis_meta: dict,
    generator: ImageGenerationService,
    refine_prompt: Optional[str] = None,
) -> GenerationResponse:
    job = generator.get_status(job_id)
    first_image = job.images[0] if job and job.images else None
    image_url = first_image.image_url if first_image else None
    mime, b64 = _extract_image_parts(image_url)
    file_name = f"{job_id}_{slot_name}.png"
    prompt = ""
    if first_image:
        file_name = Path(first_image.file_path).name if first_image.file_path else f"{job_id}_{slot_name}.png"
        prompt = first_image.prompt or ""

    return GenerationResponse(
        job_id=job_id,
        status=status,
        imageUrl=image_url,
        imageBuffer=b64,
        imageMimeType=mime,
        imageFileName=file_name,
        prompt=prompt,
        refinePrompt=refine_prompt,
        rawResponse=analysis_meta.get("pipeline") or {},
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
        slot_name=slot_name,
        analysis_meta=analysis_meta,
        generator=generator,
    )


async def _run_refinement(
    generator: ImageGenerationService,
    project_id: str,
    context_id: str,
    source_job_id: Optional[str],
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

    # Context: Prefer exact source job output for this slot, then fallback to latest slot image.
    prev_img = None
    if source_job_id:
        source_job = generator.get_status(source_job_id)
        if source_job and source_job.images:
            matched = next((img for img in source_job.images if img.slot_name == slot_name), None)
            if matched and matched.image_url:
                prev_img = matched.image_url
    if not prev_img:
        prev_img = get_generated_image_url(project_id, slot_name)
    if prev_img:
        # Keep slot-specific image first so refine uses exact per-route context by default.
        assets.insert(0, Asset(type="product_photo", url=prev_img))

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
                "summary": "Main product image using integration project payload",
                "value": {
                    "style_template": "playful",
                    "project": {
                        "name": "string",
                        "brandName": "string",
                        "productCategory": "string",
                        "targetMarketplace": "OTHER",
                        "status": "ACTIVE",
                        "mainImage": "https://example.com/main-image.png",
                        "brandLogoAssetId": None,
                        "sku": "string",
                        "shortDescription": "string",
                        "brandFontHeading": "string",
                        "brandFontSubheading": "string",
                        "createdAt": "2026-02-26T08:13:59.828Z",
                        "updatedAt": "2026-02-26T08:13:59.828Z",
                        "imagesCreated": 0,
                        "productsOptimized": 0
                    },
                    "image_url": "data:image/png;base64,REPLACE_WITH_REAL_BASE64_IMAGE"
                }
            },
            "local_file": {
                "summary": "Local file path (auto-converted to data URL)",
                "value": {
                    "style_template": "minimal",
                    "project": {
                        "name": "string",
                        "brandName": "string",
                        "productCategory": "string",
                        "targetMarketplace": "OTHER"
                    },
                    "image_url": "C:\\\\Users\\\\YourName\\\\Pictures\\\\product.png"
                }
            }
        }
    ),
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    if payload.project:
        _save_defaults_from_project_payload(project_id, payload.project)
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
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_latest_project_and_context()
    merged = _merge_slot_inputs(project_id, "generate", "key_facts", {})
    assets = []
    img1 = get_generated_image_url(project_id, "main_product") or get_asset_url(project_id, "main_raw")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    facts = [f for f in (merged.get("key_facts") or []) if f and str(f).strip()]
    if not facts:
        _, _, product = build_base_request(project_id)
        facts = product.usps[:4] if product.usps else []
    facts_text = "; ".join(facts) if facts else "Use analyzed product facts from context."
    bg_style = merged.get("background_style", "Minimal")
    logo_pos = merged.get("logo_position", "Top")
    style_template = merged.get("style_template", "playful")
    return await _run_generation(
        generator, project_id, context_id, "key_facts",
        instructions=f"Create a product infographic. Background: {bg_style}. Logo: {logo_pos}. Facts: {facts_text}.",
        emphasis=facts,
        assets=assets,
        style_template=style_template,
        remove_background=False
    )

# 3. Lifestyle
@router.post("/generate/lifestyle", response_model=GenerationResponse, summary="3. Generate Lifestyle")
async def generate_image3(
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_latest_project_and_context()
    merged = _merge_slot_inputs(project_id, "generate", "lifestyle", {})
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))
    ref_image_url = merged.get("ref_image_url")
    if ref_image_url:
        assets.append(Asset(type="product_photo", url=normalize_image_url(ref_image_url)))

    scenario = merged.get("scenario", "Use previous lifestyle context for a marketplace-ready scene.")
    style_template = merged.get("style_template", "playful")
    return await _run_generation(
        generator, project_id, context_id, "lifestyle",
        instructions=f"Lifestyle scene: {scenario}",
        assets=assets,
        style_template=style_template,
        remove_background=False
    )

# 4. USP Highlight
@router.post("/generate/usps", response_model=GenerationResponse, summary="4. Generate USP Highlight")
async def generate_image4(
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_latest_project_and_context()
    merged = _merge_slot_inputs(project_id, "generate", "usps", {})
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    usps = [u for u in (merged.get("usps") or []) if u and str(u).strip()]
    if not usps:
        _, _, product = build_base_request(project_id)
        usps = product.usps[:4] if product.usps else []
    usp_text = "; ".join(usps) if usps else "Use previous USP context."
    style_template = merged.get("style_template", "playful")
    return await _run_generation(
        generator, project_id, context_id, "usps",
        instructions=f"USP Highlights: {usp_text}",
        emphasis=usps,
        assets=assets,
        style_template=style_template,
        remove_background=False
    )

# 5. Comparison
@router.post("/generate/comparison", response_model=GenerationResponse, summary="5. Generate Comparison")
async def generate_image5(
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_latest_project_and_context()
    merged = _merge_slot_inputs(project_id, "generate", "comparison", {})
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    advantages = [a for a in (merged.get("advantages") or []) if a and str(a).strip()]
    limitations = [l for l in (merged.get("limitations") or []) if l and str(l).strip()]
    all_items = [f"ADV:{a}" for a in advantages] + [f"LIM:{l}" for l in limitations]
    style_template = merged.get("style_template", "playful")
    return await _run_generation(
        generator, project_id, context_id, "comparison",
        instructions="Comparison infographic. Left: Advantages (Green). Right: Limitations (Red).",
        emphasis=all_items,
        assets=assets,
        style_template=style_template,
        remove_background=False
    )

# 6. Cross-Selling
@router.post("/generate/cross-selling", response_model=GenerationResponse, summary="6. Generate Cross-Selling")
async def generate_image6(
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_latest_project_and_context()
    merged = _merge_slot_inputs(project_id, "generate", "cross_selling", {})
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    product_names = [n for n in (merged.get("product_names") or []) if n and str(n).strip()]
    style_template = merged.get("style_template", "playful")
    return await _run_generation(
        generator, project_id, context_id, "cross_selling",
        instructions=f"Cross-selling grid: {', '.join(product_names)}" if product_names else "Refine cross-selling layout with previous context.",
        emphasis=product_names,
        assets=assets,
        style_template=style_template,
        remove_background=False
    )

# 7. Closing
@router.post("/generate/closing", response_model=GenerationResponse, summary="7. Generate Closing")
async def generate_image7(
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_latest_project_and_context()
    merged = _merge_slot_inputs(project_id, "generate", "closing", {})
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    direction = merged.get("direction", "Emotional")
    headline = merged.get("headline")
    emphasis = [headline] if headline else []
    style_template = merged.get("style_template", "playful")
    return await _run_generation(
        generator, project_id, context_id, "closing",
        instructions=f"Closing image. Direction: {direction}. Headline: {headline or 'None'}",
        emphasis=emphasis,
        assets=assets,
        style_template=style_template,
        remove_background=False
    )


# --- REFINEMENT ENDPOINTS ---

@router.post("/refine/main-product", response_model=GenerationResponse, summary="Refine Main Product")
async def refine_image1(
    payload: Image1RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "main_product", payload.model_dump(exclude_none=True))
    image_source = merged.get("image_url") or get_generated_image_url(project_id, "main_product") or get_asset_url(project_id, "main_raw")
    if not image_source:
        raise HTTPException(status_code=400, detail="No source image available for main-product refinement.")
    normalized = normalize_image_url(image_source)
    assets = [Asset(type="product_photo", url=normalized)]
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "main_product",
        instructions="Create a marketplace-ready product image. Pure white background. Product centered. No text.",
        feedback=merged.get("feedback", payload.feedback),
        assets=assets,
        style_template=merged.get("style_template", payload.style_template),
        remove_background=True
    )

@router.post("/refine/key-facts", response_model=GenerationResponse, summary="Refine Key Facts")
async def refine_image2(
    payload: Image2RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "key_facts", payload.model_dump(exclude_none=True))
    # Context logic same as generation (plus the generated image fetched by _run_refinement)
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    facts = [f for f in (merged.get("key_facts") or []) if f and str(f).strip()]
    facts_text = "; ".join(facts) if facts else "Use previous key fact text context"
    bg_style = merged.get("background_style", "Keep previous style")
    logo_pos = merged.get("logo_position", "Keep previous logo placement")
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "key_facts",
        instructions=f"Refine product infographic. Background: {bg_style}. Logo: {logo_pos}. Facts: {facts_text}.",
        feedback=merged.get("feedback", payload.feedback),
        emphasis=facts,
        assets=assets,
        style_template=merged.get("style_template", payload.style_template)
    )

@router.post("/refine/lifestyle", response_model=GenerationResponse, summary="Refine Lifestyle")
async def refine_image3(
    payload: Image3RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "lifestyle", payload.model_dump(exclude_none=True))
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))
    if merged.get("ref_image_url"):
        assets.append(Asset(type="product_photo", url=normalize_image_url(merged.get("ref_image_url"))))

    scenario_text = merged.get("scenario", "Keep previous lifestyle scenario context")
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "lifestyle",
        instructions=f"Lifestyle scene: {scenario_text}",
        feedback=merged.get("feedback", payload.feedback),
        assets=assets,
        style_template=merged.get("style_template", payload.style_template)
    )

@router.post("/refine/usps", response_model=GenerationResponse, summary="Refine USP Highlight")
async def refine_image4(
    payload: Image4RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "usps", payload.model_dump(exclude_none=True))
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    usps = [u for u in (merged.get("usps") or []) if u and str(u).strip()]
    usp_text = "; ".join(usps) if usps else "Keep previous USP text context"
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "usps",
        instructions=f"USP Highlights: {usp_text}",
        feedback=merged.get("feedback", payload.feedback),
        emphasis=usps,
        assets=assets,
        style_template=merged.get("style_template", payload.style_template)
    )

@router.post("/refine/comparison", response_model=GenerationResponse, summary="Refine Comparison")
async def refine_image5(
    payload: Image5RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "comparison", payload.model_dump(exclude_none=True))
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))
    
    advantages = [a for a in (merged.get("advantages") or []) if a and str(a).strip()]
    limitations = [l for l in (merged.get("limitations") or []) if l and str(l).strip()]
    all_items = [f"ADV:{a}" for a in advantages] + [f"LIM:{l}" for l in limitations]
    comp_instruction = "Comparison infographic. Left: Advantages (Green). Right: Limitations (Red)."
    if not all_items:
        comp_instruction = "Refine existing comparison infographic layout and clarity using previous text context."
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "comparison",
        instructions=comp_instruction,
        feedback=merged.get("feedback", payload.feedback),
        emphasis=all_items,
        assets=assets,
        style_template=merged.get("style_template", payload.style_template)
    )

@router.post("/refine/cross-selling", response_model=GenerationResponse, summary="Refine Cross-Selling")
async def refine_image6(
    payload: Image6RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "cross_selling", payload.model_dump(exclude_none=True))
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    product_names = [n for n in (merged.get("product_names") or []) if n and str(n).strip()]
    cs_instruction = f"Cross-selling grid: {', '.join(product_names)}" if product_names else "Refine existing cross-selling layout using previous context."
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "cross_selling",
        instructions=cs_instruction,
        feedback=merged.get("feedback", payload.feedback),
        emphasis=product_names,
        assets=assets,
        style_template=merged.get("style_template", payload.style_template)
    )

@router.post("/refine/closing", response_model=GenerationResponse, summary="Refine Closing")
async def refine_image7(
    payload: Image7RefineRequest,
    generator: ImageGenerationService = Depends(get_image_generation_service)
):
    project_id, context_id = _resolve_project_and_context(payload)
    merged = _merge_slot_inputs(project_id, "refine", "closing", payload.model_dump(exclude_none=True))
    assets = []
    img1 = get_generated_image_url(project_id, "main_product")
    if img1:
        assets.append(Asset(type="product_photo", url=img1))

    headline = merged.get("headline")
    emphasis = [headline] if headline else []
    direction = merged.get("direction", "Keep previous direction")
    headline_text = headline or "Use previous headline context"
    return await _run_refinement(
        generator, project_id, context_id, getattr(payload, "job_id", None), "closing",
        instructions=f"Closing image. Direction: {direction}. Headline: {headline_text}",
        feedback=merged.get("feedback", payload.feedback),
        emphasis=emphasis,
        assets=assets,
        style_template=merged.get("style_template", payload.style_template)
    )


@router.get("/jobs/{job_id}", response_model=GenerationStatus, summary="Check Job Status")
async def get_job_status(job_id: str, store: InMemoryJobStore = Depends(get_job_store)):
    job = store.get(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    return GenerationStatus(job_id=job_id, status=job.status, images=job.images)
