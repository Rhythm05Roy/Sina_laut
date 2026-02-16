import json
import pathlib
import time
from typing import Any, Dict, List

import requests
import base64
import streamlit as st

# ---------- Config ----------
st.set_page_config(page_title="Sina Laut AI", layout="wide")
DEFAULT_BASE_URL = "http://127.0.0.1:8000/api"

SLOTS = [
    ("main_product",  "Main Product",   "📦"),
    ("key_facts",     "Key Facts",      "✨"),
    ("lifestyle",     "Lifestyle",      "💛"),
    ("usps",          "USP Highlight",  "👤"),
    ("comparison",    "Comparison",     "📊"),
    ("cross_selling", "Cross-Selling",  "🛒"),
    ("closing",       "Closing",        "💜"),
]

STYLE_TEMPLATES = [
    ("playful", "Playful (Playmobil style)"),
    ("modern",  "Modern / Clean"),
    ("minimal", "Minimal"),
]

BACKGROUND_STYLES = ["Minimal", "Gradient", "Solid Color", "Pattern"]
LOGO_POSITIONS   = ["Top", "Bottom", "Top-Left", "Top-Right", "None"]

AVAILABLE_LANGUAGES = ["English", "German", "French", "Spanish", "Italian", "Polish", "Dutch"]
LANG_CODE_MAP = {
    "English": "en", "German": "de", "French": "fr", "Spanish": "es",
    "Italian": "it", "Polish": "pl", "Dutch": "nl",
}

FONT_OPTIONS = [
    "Inter", "Roboto", "Open Sans", "Lato", "Montserrat",
    "Poppins", "Raleway", "Nunito", "Playfair Display", "Oswald",
]


# ------------------------------------------------------------------ #
#  Custom CSS                                                         #
# ------------------------------------------------------------------ #
def inject_css():
    st.markdown("""
    <style>
    /* ---------- global ---------- */
    .block-container { max-width: 960px; margin: auto; padding-top: 2rem; }
    [data-testid="stAppViewContainer"] { background: #e8ecf1; }

    /* ---------- stepper ---------- */
    .stepper { display:flex; align-items:center; justify-content:center; gap:0; margin-bottom:2rem; }
    .step-circle {
        width:44px; height:44px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        font-weight:700; font-size:16px; color:#fff;
        background:#c2c8d0; position:relative; z-index:2;
        transition: background .25s;
    }
    .step-circle.active  { background:#1b2537; }
    .step-circle.done    { background:#1b2537; }
    .step-line  { width:60px; height:3px; background:#c2c8d0; z-index:1; }
    .step-line.done { background:#1b2537; }

    /* ---------- card ---------- */
    .wizard-card {
        background:#fff; border-radius:14px; padding:2.5rem 2.5rem 2rem;
        box-shadow:0 1px 4px rgba(0,0,0,.06); margin-bottom:1.5rem;
    }

    /* ---------- buttons ---------- */
    div[data-testid="stButton"] button {
        border-radius:8px; padding:.5rem 1.6rem; font-weight:600; font-size:.9rem;
    }

    /* ---------- requirements box ---------- */
    .req-box {
        background:#f0fdf4; border-left:4px solid #22c55e;
        border-radius:8px; padding:1rem 1.2rem; font-size:.85rem;
    }
    .req-box b { color:#1b2537; }
    .req-box .item { color:#15803d; margin:4px 0; }

    /* ---------- preview panel ---------- */
    .brand-preview {
        background:#f3f0ff; border-radius:12px; padding:2rem;
        text-align:center; min-height:220px; display:flex;
        flex-direction:column; align-items:center; justify-content:center;
    }

    /* ---------- preview placeholder ---------- */
    .preview-placeholder {
        background:#f3f0ff; border-radius:12px; padding:2rem;
        text-align:center; min-height:180px; display:flex;
        flex-direction:column; align-items:center; justify-content:center;
        color:#8b95a5; border: 2px dashed #d4d4d8;
    }

    /* ---------- misc ---------- */
    .section-label { font-weight:600; font-size:.92rem; margin:1rem 0 .3rem; }

    /* ---------- generated image container ---------- */
    .gen-image-box {
        border: 1px solid #e5e7eb; border-radius:12px; padding:1rem;
        margin: 1rem 0; background: #fafbfc;
    }
    </style>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #
def call_api(method: str, url: str, **kwargs) -> requests.Response:
    func = getattr(requests, method.lower())
    return func(url, **kwargs)

def get_base_url() -> str:
    """Return the user-configured API base without trailing slash."""
    return st.session_state.get("base_url", DEFAULT_BASE_URL).rstrip("/")


def build_payload(project, brand, product, assets, briefs, remove_bg, style_template):
    return {
        "project": project,
        "brand": brand,
        "product": product,
        "assets": assets,
        "image_briefs": briefs,
        "remove_background": remove_bg,
        "style_template": style_template,
    }


def to_data_url(upload) -> str:
    if upload is None:
        return ""
    mime = upload.type or "application/octet-stream"
    b64 = base64.b64encode(upload.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def poll_job(base_url: str, job_id: str, max_wait: int = 180) -> dict | None:
    """Poll /ai/jobs/{job_id} until completed or timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            resp = call_api("get", f"{base_url}/step4/jobs/{job_id}")
            if resp.status_code < 400:
                data = resp.json()
                if data.get("status") == "completed":
                    return data
        except Exception:
            pass
        time.sleep(2)
    return None


def get_image_bytes_from_result(image_data: dict) -> bytes | None:
    """Extract displayable image bytes from a GeneratedImage result."""
    url = image_data.get("image_url", "")
    file_path = image_data.get("file_path", "")

    # Try local file first
    if file_path and pathlib.Path(file_path).exists():
        return pathlib.Path(file_path).read_bytes()

    # Try data URL
    if url and url.startswith("data:"):
        try:
            _, b64 = url.split(",", 1)
            return base64.b64decode(b64)
        except Exception:
            pass

    return None


# ------------------------------------------------------------------ #
#  Backend context guard                                             #
# ------------------------------------------------------------------ #
def ensure_backend_context() -> bool:
    """
    Make sure the FastAPI in-memory store has project, brand, and product
    for the current project_id. Useful after backend reloads, which reset
    the store and can cause Image 1 to fail with 404.
    """
    base_url = get_base_url()
    project_id = st.session_state.get("project_id")
    if not project_id:
        st.error("Project ID missing. Please complete Steps 1–3 first.")
        return False

    try:
        # Project
        resp = call_api("get", f"{base_url}/step1/project/{project_id}")
        if resp.status_code == 404:
            proj_payload = _build_project_dict()
            resp = call_api("post", f"{base_url}/step1/project/create", json=proj_payload)
            if resp.status_code >= 400:
                st.error(f"Unable to recreate project (HTTP {resp.status_code}): {resp.text}")
                return False
            project_id = resp.json().get("id")
            st.session_state.project_id = project_id
            st.session_state.generated_images = {}
            st.session_state.job_ids = []
            st.info("Backend was empty — recreated project context automatically.")
        elif resp.status_code >= 400:
            st.error(f"Project check failed (HTTP {resp.status_code}): {resp.text}")
            return False

        # Brand
        resp = call_api("get", f"{base_url}/step2/brand/project/{project_id}")
        if resp.status_code == 404:
            brand_payload = {"project_id": project_id, "brand": _build_brand_dict()}
            resp = call_api("post", f"{base_url}/step2/brand/save", json=brand_payload)
            if resp.status_code >= 400:
                st.error(f"Unable to re-save brand (HTTP {resp.status_code}): {resp.text}")
                return False
        elif resp.status_code >= 400:
            st.error(f"Brand check failed (HTTP {resp.status_code}): {resp.text}")
            return False

        # Product
        resp = call_api("get", f"{base_url}/step3/product/project/{project_id}")
        if resp.status_code == 404:
            prod_payload = {"project_id": project_id, "product": _build_product_dict()}
            resp = call_api("post", f"{base_url}/step3/product/save", json=prod_payload)
            if resp.status_code >= 400:
                st.error(f"Unable to re-save product (HTTP {resp.status_code}): {resp.text}")
                return False
        elif resp.status_code >= 400:
            st.error(f"Product check failed (HTTP {resp.status_code}): {resp.text}")
            return False
    except requests.RequestException as exc:
        st.error(f"Connection error while checking backend context: {exc}")
        return False

    return True


# ------------------------------------------------------------------ #
#  Session state defaults                                             #
# ------------------------------------------------------------------ #
DEFAULTS = {
    "current_step": 1,
    "job_ids": [],
    "project_id": None,
    # Step 1
    "project_name": "", "brand_name": "", "product_category": "", "target_marketplace": "",
    # Step 2
    "logo_file": None, "font_heading": "Inter", "font_body": "Roboto",
    "primary_color": "#6366f1", "secondary_color": "#8b5cf6",
    # Step 3
    "sku": "", "product_title": "", "short_desc": "",
    "download_format": "JPG Version",
    "usp1": "", "usp2": "", "usp3": "", "usp4": "",
    "seo_amazon": True, "seo_google": False,
    "selected_languages": ["English"],
    # Step 4
    "num_images": 7, "active_slot": 0,
    "slot_uploads": {},
    "slot_bg_style": {},
    "slot_logo_pos": {},
    "slot_facts": {},
    # Per-slot generated results  { slot_key: { "image_url":..., "file_path":..., "prompt":... } }
    "generated_images": {},
    # Per-slot refine feedback text
    "refine_text": {},
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ------------------------------------------------------------------ #
#  Stepper component                                                  #
# ------------------------------------------------------------------ #
def render_stepper(current: int, total: int = 4):
    parts = []
    for i in range(1, total + 1):
        cls = "done" if i < current else ("active" if i == current else "")
        label = "✓" if i < current else str(i)
        parts.append(f'<div class="step-circle {cls}">{label}</div>')
        if i < total:
            line_cls = "done" if i < current else ""
            parts.append(f'<div class="step-line {line_cls}"></div>')
    st.markdown(f'<div class="stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  Navigation helpers                                                 #
# ------------------------------------------------------------------ #
def go_next():
    st.session_state.current_step += 1

def go_back():
    st.session_state.current_step -= 1


def submit_step1():
    """Submit Project Setup to API."""
    base_url = get_base_url()
    payload = _build_project_dict()
    try:
        resp = call_api("post", f"{base_url}/step1/project/create", json=payload)
        if resp.status_code >= 400:
            st.error(f"Error {resp.status_code}: {resp.text}")
            return
        data = resp.json()
        st.session_state.project_id = data.get("id")
        st.success("✅ Project created!")
        time.sleep(0.5)
        go_next()
    except Exception as e:
        st.error(f"Connection error: {e}")

def submit_step2():
    """Submit Brand CI to API."""
    base_url = get_base_url()
    project_id = st.session_state.get("project_id")
    if not project_id:
        st.error("Project ID missing. Please go back to Step 1.")
        return

    brand_data = _build_brand_dict()
    payload = {"project_id": project_id, "brand": brand_data}
    
    try:
        resp = call_api("post", f"{base_url}/step2/brand/save", json=payload)
        if resp.status_code >= 400:
            st.error(f"Error {resp.status_code}: {resp.text}")
            return
        st.success("✅ Brand saved!")
        time.sleep(0.5)
        go_next()
    except Exception as e:
        st.error(f"Connection error: {e}")

def submit_step3():
    """Submit Product Info to API."""
    base_url = get_base_url()
    project_id = st.session_state.get("project_id")
    if not project_id:
        st.error("Project ID missing. Please go back to Step 1.")
        return

    product_data = _build_product_dict()
    payload = {"project_id": project_id, "product": product_data}

    try:
        resp = call_api("post", f"{base_url}/step3/product/save", json=payload)
        if resp.status_code >= 400:
            st.error(f"Error {resp.status_code}: {resp.text}")
            return
        st.success("✅ Product info saved!")
        time.sleep(0.5)
        go_next()
    except Exception as e:
        st.error(f"Connection error: {e}")


# ------------------------------------------------------------------ #
#  Shared helpers — build project / brand / product dicts             #
# ------------------------------------------------------------------ #
def _build_project_dict():
    mkts = []
    if st.session_state.seo_amazon:
        mkts.append("amazon")
    if st.session_state.seo_google:
        mkts.append("google")
    if not mkts:
        mkts = [st.session_state.target_marketplace.lower()] if st.session_state.target_marketplace else ["amazon"]
    return {
        "project_name": st.session_state.project_name,
        "brand_name": st.session_state.brand_name,
        "product_category": st.session_state.product_category,
        "target_marketplaces": mkts,
    }


def _build_brand_dict():
    logo_url = to_data_url(st.session_state.logo_file) if st.session_state.logo_file else None
    return {
        "logo_url": logo_url,
        "primary_color": st.session_state.primary_color,
        "secondary_color": st.session_state.secondary_color,
        "font_heading": st.session_state.font_heading,
        "font_body": st.session_state.font_body,
    }


def _build_product_dict():
    usps = [u for u in [st.session_state.usp1, st.session_state.usp2,
                         st.session_state.usp3, st.session_state.usp4] if u]
    lang_codes = [LANG_CODE_MAP.get(l, l.lower()[:2]) for l in st.session_state.selected_languages]
    return {
        "sku": st.session_state.sku,
        "title": st.session_state.product_title,
        "short_description": st.session_state.short_desc,
        "usps": usps,
        "keywords": {"primary": [], "secondary": []},
        "languages": lang_codes,
    }


# ------------------------------------------------------------------ #
#  Generate a single slot image                                       #
# ------------------------------------------------------------------ #
def generate_single_image(slot_key: str, extra_instructions: str = "",
                          input_image_uploads: list | None = None,
                          emphasis_items: list | None = None):
    """Call specific /api/step4/generate/{slot_key} endpoint and poll job."""
    base_url = get_base_url()
    project_id = st.session_state.get("project_id")
    if not project_id:
        st.error("Project ID missing. Please complete Step 1 first.")
        return
    if not ensure_backend_context():
        return
    project_id = st.session_state.get("project_id")

    # Payload base
    payload = {
        "project_id": project_id,
        "style_template": "playful", # Default or fetch from somewhere global if needed
    }

    # Endpoint suffix mapping
    endpoint_map = {
        "main_product": "main-product",
        "key_facts": "key-facts",
        "lifestyle": "lifestyle",
        "usps": "usps",
        "comparison": "comparison",
        "cross_selling": "cross-selling",
        "closing": "closing",
    }
    suffix = endpoint_map.get(slot_key)
    if not suffix:
        st.error(f"Unknown slot: {slot_key}")
        return

    # Specific payload construction
    if slot_key == "main_product":
        main_upload = st.session_state.slot_uploads.get("main_product")
        if not main_upload:
            st.error("Please upload main product image.")
            return
        payload["image_url"] = to_data_url(main_upload)

    elif slot_key == "key_facts":
        facts = emphasis_items if emphasis_items else st.session_state.slot_facts.get(slot_key, [])
        payload["key_facts"] = [f for f in facts if f.strip()]
        payload["background_style"] = st.session_state.slot_bg_style.get(slot_key, "Minimal")
        payload["logo_position"] = st.session_state.slot_logo_pos.get(slot_key, "Top")

    elif slot_key == "lifestyle":
        # extract scenario from somewhere?
        # In UI, scenario_desc is local variable inside step_image_setup.
        # But generate_single_image called with extra_instructions which has it?
        # extra_instructions has "Create a lifestyle scene: {scenario_desc}..."
        # But API expects "scenario" string.
        # I need to extract it or pass it explicitly.
        # Current UI implementation: extra_instructions HAS the full prompt.
        # New API expects dedicated field.
        # Hack: Pass scenario as argument or global session state?
        # Better: Since specific logic is inside this function now, I need specific arguments.
        # But signature is generic.
        # For lifestyle, "extra_instructions" was heavily formatted.
        # I should change the calling code to pass arguments cleaner.
        # OR parse it back? No.
        # I will rely on `st.session_state.lifestyle_scenario` if stored.
        # Let's check UI call site.
        # UI: `scenario_desc = st.text_area(..., key="lifestyle_scenario")`
        # So I can use `st.session_state.lifestyle_scenario`.
        scenario = st.session_state.get("lifestyle_scenario", "")
        payload["scenario"] = scenario
        # Reference image
        ref = st.session_state.slot_uploads.get("lifestyle")
        if ref:
             payload["ref_image_url"] = to_data_url(ref)

    elif slot_key == "usps":
        usps = emphasis_items if emphasis_items else st.session_state.slot_facts.get("usps", [])
        payload["usps"] = [u for u in usps if u.strip()]

    elif slot_key == "comparison":
        payload["advantages"] = [a for a in st.session_state.get("advantages", []) if a.strip()]
        payload["limitations"] = [l for l in st.session_state.get("limitations", []) if l.strip()]

    elif slot_key == "cross_selling":
        prods = emphasis_items if emphasis_items else st.session_state.get("cross_sell_products", [])
        payload["product_names"] = [p for p in prods if p.strip()]

    elif slot_key == "closing":
        payload["direction"] = st.session_state.get("closing_direction", "Emotional")
        payload["headline"] = st.session_state.get("closing_headline", "")


    with st.spinner(f"Generating {slot_key} image…"):
        try:
            resp = call_api("post", f"{base_url}/step4/generate/{suffix}", json=payload)
            if resp.status_code >= 400:
                st.error(f"Error {resp.status_code}: {resp.text}")
                return
            data = resp.json()
            job_id = data.get("job_id")
            if job_id:
                st.session_state.job_ids.append(job_id)
            # Poll
            result = poll_job(base_url, job_id)
            if result and result.get("images"):
                img = result["images"][0]
                st.session_state.generated_images[slot_key] = img
                st.success("✅ Image generated!")
            else:
                st.warning("Generation timed out – check Jobs tab.")
        except Exception as e:
            st.error(f"Connection error: {e}")


# ------------------------------------------------------------------ #
#  Refine a single slot image                                         #
# ------------------------------------------------------------------ #
def refine_single_image(slot_key: str, feedback: str):
    """Call specific /api/step4/refine/{slot_key} endpoint and poll job."""
    base_url = get_base_url()
    project_id = st.session_state.get("project_id")
    if not project_id:
        st.error("Project ID missing. Context lost.")
        return
    if not ensure_backend_context():
        return
    project_id = st.session_state.get("project_id")

    # Payload base
    payload = {
        "project_id": project_id,
        "style_template": "playful",
        "feedback": feedback,
    }

    endpoint_map = {
        "main_product": "main-product",
        "key_facts": "key-facts",
        "lifestyle": "lifestyle",
        "usps": "usps",
        "comparison": "comparison",
        "cross_selling": "cross-selling",
        "closing": "closing",
    }
    suffix = endpoint_map.get(slot_key)
    if not suffix:
        st.error(f"Unknown slot: {slot_key}")
        return

    # Reconstruct payload fields needed for the request schema
    if slot_key == "main_product":
        main_upload = st.session_state.slot_uploads.get("main_product")
        if main_upload:
             payload["image_url"] = to_data_url(main_upload)
        else:
             # If strictly required by schema but we are refining, we might not have it if session reset?
             # But session persists.
             st.error("Main product upload missing.")
             return

    elif slot_key == "key_facts":
        facts = st.session_state.slot_facts.get(slot_key, [])
        payload["key_facts"] = [f for f in facts if f.strip()]
        payload["background_style"] = st.session_state.slot_bg_style.get(slot_key, "Minimal")
        payload["logo_position"] = st.session_state.slot_logo_pos.get(slot_key, "Top")

    elif slot_key == "lifestyle":
        scenario = st.session_state.get("lifestyle_scenario", "")
        payload["scenario"] = scenario
        ref = st.session_state.slot_uploads.get("lifestyle")
        if ref:
             payload["ref_image_url"] = to_data_url(ref)

    elif slot_key == "usps":
        usps = st.session_state.slot_facts.get("usps", [])
        payload["usps"] = [u for u in usps if u.strip()]

    elif slot_key == "comparison":
        payload["advantages"] = [a for a in st.session_state.get("advantages", []) if a.strip()]
        payload["limitations"] = [l for l in st.session_state.get("limitations", []) if l.strip()]

    elif slot_key == "cross_selling":
        prods = st.session_state.get("cross_sell_products", [])
        payload["product_names"] = [p for p in prods if p.strip()]

    elif slot_key == "closing":
        payload["direction"] = st.session_state.get("closing_direction", "Emotional")
        payload["headline"] = st.session_state.get("closing_headline", "")


    with st.spinner(f"Refining {slot_key} image…"):
        try:
            # Note: RefineRequest is the body. It includes feedback + original fields.
            resp = call_api("post", f"{base_url}/step4/refine/{suffix}", json=payload)
            if resp.status_code >= 400:
                st.error(f"Error {resp.status_code}: {resp.text}")
                return
            data = resp.json()
            job_id = data.get("job_id")
            if job_id:
                st.session_state.job_ids.append(job_id)
            result = poll_job(base_url, job_id)
            if result and result.get("images"):
                img = result["images"][0]
                st.session_state.generated_images[slot_key] = img
                st.success("✅ Image refined!")
            else:
                st.warning("Refinement timed out – check Jobs tab.")
        except Exception as e:
            st.error(f"Connection error: {e}")


# ------------------------------------------------------------------ #
#  Show preview + refine + download for a generated image             #
# ------------------------------------------------------------------ #
def show_preview_refine_download(slot_key: str, slot_label: str):
    """If an image has been generated for this slot, show preview, refine, download."""
    img_data = st.session_state.generated_images.get(slot_key)
    if not img_data:
        return

    st.markdown("---")
    st.markdown(f"**🖼️ Generated Preview — {slot_label}**")

    # Display the image
    img_url = img_data.get("image_url", "")
    file_path = img_data.get("file_path", "")

    if file_path and pathlib.Path(file_path).exists():
        st.image(file_path, use_column_width=True)
    elif img_url:
        st.image(img_url, use_column_width=True)

    # Download button
    img_bytes = get_image_bytes_from_result(img_data)
    if img_bytes:
        ext = "png"
        mime = "image/png"
        if st.session_state.download_format == "JPG Version":
            ext = "jpg"
            mime = "image/jpeg"
        elif st.session_state.download_format == "WebP Version":
            ext = "webp"
            mime = "image/webp"
        st.download_button(
            f"⬇️ Download {slot_label}",
            data=img_bytes,
            file_name=f"{slot_key}.{ext}",
            mime=mime,
            key=f"dl_{slot_key}",
        )

    # Refine section
    st.markdown("**🔄 Refine this image**")
    refine_fb = st.text_input(
        "Refinement instructions",
        value=st.session_state.refine_text.get(slot_key, ""),
        placeholder="e.g., make the background brighter, add more contrast…",
        key=f"refine_input_{slot_key}",
    )
    st.session_state.refine_text[slot_key] = refine_fb

    if st.button(f"🔄 Refine", key=f"refine_btn_{slot_key}"):
        if refine_fb.strip():
            refine_single_image(slot_key, refine_fb.strip())
            st.rerun()
        else:
            st.warning("Please enter refinement instructions.")


# ------------------------------------------------------------------ #
#  STEP 1  —  Project Setup                                           #
# ------------------------------------------------------------------ #
def step_project_setup():
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("## Project Setup")

    st.session_state.project_name = st.text_input(
        "Project Name *", value=st.session_state.project_name,
        placeholder="e.g., Summer Collection 2024", key="inp_proj_name",
    )
    st.session_state.brand_name = st.text_input(
        "Brand Name *", value=st.session_state.brand_name,
        placeholder="e.g., EcoStyle", key="inp_brand_name",
    )
    st.session_state.product_category = st.text_input(
        "Product Category *", value=st.session_state.product_category,
        placeholder="e.g., Fashion", key="inp_category",
    )
    st.session_state.target_marketplace = st.text_input(
        "Target Marketplace *", value=st.session_state.target_marketplace,
        placeholder="e.g., Amazon", key="inp_marketplace",
    )

    st.markdown('</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← Cancel", key="cancel_1", disabled=True)
    with col_r:
        valid = all([
            st.session_state.project_name,
            st.session_state.brand_name,
            st.session_state.product_category,
            st.session_state.target_marketplace,
        ])
        st.button("Next →", key="next_1", on_click=submit_step1, disabled=not valid)


# ------------------------------------------------------------------ #
#  STEP 2  —  Brand CI Setup                                          #
# ------------------------------------------------------------------ #
def step_brand_ci():
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("## Brand CI Setup")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Brand Logo \\***")
        logo = st.file_uploader(
            "Upload Logo", type=["png", "jpg", "jpeg", "svg"],
            label_visibility="collapsed", key="inp_logo",
        )
        if logo:
            st.session_state.logo_file = logo
        st.caption("PNG, JPG or SVG (max. 5 MB)")

        st.markdown('<p class="section-label">Font Selection <span style="font-weight:400; font-size:.8rem;">'
                    '( First one Heading, Second one Sub Heading )</span></p>', unsafe_allow_html=True)
        st.session_state.font_heading = st.selectbox(
            "Heading Font", FONT_OPTIONS,
            index=FONT_OPTIONS.index(st.session_state.font_heading),
            key="inp_font_h",
        )
        st.session_state.font_body = st.selectbox(
            "Sub Heading Font", FONT_OPTIONS,
            index=FONT_OPTIONS.index(st.session_state.font_body),
            key="inp_font_b",
        )

    with col_right:
        st.markdown("**Brand Preview**")
        preview_html = '<div class="brand-preview">'
        if st.session_state.logo_file:
            data_url = to_data_url(st.session_state.logo_file)
            preview_html += f'<img src="{data_url}" style="max-height:80px; margin-bottom:12px;" />'
        else:
            preview_html += '<div style="font-size:2.5rem; margin-bottom:8px;">🎨</div>'
        preview_html += f'<div style="font-size:1.6rem; font-weight:700; font-family:{st.session_state.font_heading},sans-serif; margin-bottom:4px;">zZZ</div>'
        preview_html += f'<div style="font-size:.85rem; color:#666; font-family:{st.session_state.font_body},sans-serif;">Font: {st.session_state.font_heading}, {st.session_state.font_body}</div>'
        preview_html += '</div>'
        st.markdown(preview_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← Back", key="back_2", on_click=go_back)
    with col_r:
        st.button("Next →", key="next_2", on_click=submit_step2)


# ------------------------------------------------------------------ #
#  STEP 3  —  Product Information                                     #
# ------------------------------------------------------------------ #
def step_product_info():
    st.markdown('<div class="wizard-card">', unsafe_allow_html=True)
    st.markdown("## Product Information")

    c1, c2 = st.columns(2)
    with c1:
        st.session_state.sku = st.text_input(
            "Article Number / SKU *", value=st.session_state.sku,
            placeholder="e.g., SKU-12345", key="inp_sku",
        )
    with c2:
        st.session_state.product_title = st.text_input(
            "Product Title *", value=st.session_state.product_title,
            placeholder="e.g., Premium Wireless Headphones", key="inp_title",
        )

    st.session_state.short_desc = st.text_area(
        "Short Product Description *", value=st.session_state.short_desc,
        placeholder="Brief description of your product...", key="inp_desc", height=90,
    )

    st.session_state.download_format = st.selectbox(
        "Download Image *", ["JPG Version", "PNG Version", "WebP Version"],
        index=["JPG Version", "PNG Version", "WebP Version"].index(st.session_state.download_format),
        key="inp_dl_fmt",
    )

    # USPs
    st.markdown('<p class="section-label">USP Section (Unique Selling Points)</p>', unsafe_allow_html=True)
    u1, u2 = st.columns(2)
    with u1:
        st.session_state.usp1 = st.text_input("USP 1", value=st.session_state.usp1, key="inp_usp1", label_visibility="collapsed", placeholder="USP 1")
        st.session_state.usp3 = st.text_input("USP 3", value=st.session_state.usp3, key="inp_usp3", label_visibility="collapsed", placeholder="USP 3")
    with u2:
        st.session_state.usp2 = st.text_input("USP 2", value=st.session_state.usp2, key="inp_usp2", label_visibility="collapsed", placeholder="USP 2")
        st.session_state.usp4 = st.text_input("USP 4", value=st.session_state.usp4, key="inp_usp4", label_visibility="collapsed", placeholder="USP 4")

    # SEO
    st.markdown('<p class="section-label">Keyword & SEO Settings</p>', unsafe_allow_html=True)
    st.session_state.seo_amazon = st.checkbox("Optimize keywords for Amazon", value=st.session_state.seo_amazon, key="inp_seo_az")
    st.session_state.seo_google = st.checkbox("Optimize keywords for Google", value=st.session_state.seo_google, key="inp_seo_gg")

    # Languages
    st.markdown('<p class="section-label">Language Selection (Select up to 7 languages)</p>', unsafe_allow_html=True)
    st.session_state.selected_languages = st.multiselect(
        "Languages", AVAILABLE_LANGUAGES,
        default=st.session_state.selected_languages,
        max_selections=7, key="inp_langs", label_visibility="collapsed",
    )
    st.caption(f"Selected: {len(st.session_state.selected_languages)} / 7 languages")

    st.markdown('</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← Back", key="back_3", on_click=go_back)
    with col_r:
        valid = all([st.session_state.sku, st.session_state.product_title, st.session_state.short_desc])
        st.button("Continue to Image Setup →", key="next_3", on_click=submit_step3, disabled=not valid)


# ------------------------------------------------------------------ #
#  STEP 4  —  Image Setup (per-image generate → preview → refine)     #
# ------------------------------------------------------------------ #
def step_image_setup():
    sidebar_col, content_col = st.columns([1, 2.6])

    active = st.session_state.active_slot
    num = st.session_state.num_images

    # ---------- left sidebar ----------
    with sidebar_col:
        st.markdown("**Number of Images**")
        st.session_state.num_images = st.selectbox(
            "Number", list(range(1, 8)), index=num - 1,
            key="inp_num_imgs", label_visibility="collapsed",
        )
        num = st.session_state.num_images

        st.markdown("---")
        for i in range(num):
            slot_key, label, icon = SLOTS[i]
            is_active = (i == active)
            has_image = slot_key in st.session_state.generated_images
            status_icon = "✅" if has_image else "○"
            if st.button(
                f"{icon}  Image {i+1} — {label}  {status_icon}",
                key=f"slot_btn_{i}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_slot = i
                st.rerun()

    # ---------- right content ----------
    with content_col:
        if active >= num:
            st.session_state.active_slot = 0
            active = 0

        slot_key, slot_label, slot_icon = SLOTS[active]

        # ========================== IMAGE 1: MAIN PRODUCT ==========================
        if slot_key == "main_product":
            st.markdown("### Image 1 – Main Product Image")
            st.caption("Upload your product image. AI will process it to be marketplace-ready.")

            st.markdown("""
            <div class="req-box">
                <b>AI will apply these requirements:</b>
                <div class="item">✓ Pure white background (#FFFFFF)</div>
                <div class="item">✓ Product centered and fills 85% of frame</div>
                <div class="item">✓ No text or additional graphics</div>
                <div class="item">✓ High resolution (minimum 1000px)</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")

            upload = st.file_uploader(
                "Upload product photo *", type=["png", "jpg", "jpeg"],
                key="upload_main",
            )
            if upload:
                st.session_state.slot_uploads[slot_key] = upload
                st.image(upload, caption="Uploaded product photo", width=300)

            if st.button("🚀 Generate Main Image", key="gen_main", type="primary",
                         disabled=not st.session_state.slot_uploads.get("main_product")):
                generate_single_image(
                    "main_product",
                    extra_instructions=(
                        "Create a marketplace-ready product image. "
                        "Pure white background (#FFFFFF). "
                        "Product centered and fills 85% of frame. "
                        "No text or additional graphics. "
                        "High resolution, professional quality."
                    ),
                )
                st.rerun()

            # Show preview / refine / download
            show_preview_refine_download("main_product", "Main Product")

        # ========================== IMAGE 2: KEY FACTS ==========================
        elif slot_key == "key_facts":
            st.markdown("### Image 2 – Product with Key Facts")
            st.caption("Uses Image 1 as context + your key facts to generate an infographic.")

            if "main_product" not in st.session_state.generated_images:
                st.warning("⚠️ Please generate Image 1 (Main Product) first — it is used as context for this image.")

            st.session_state.slot_bg_style[slot_key] = st.selectbox(
                "Background Style", BACKGROUND_STYLES,
                index=BACKGROUND_STYLES.index(st.session_state.slot_bg_style.get(slot_key, "Minimal")),
                key="bg_style_kf",
            )
            st.session_state.slot_logo_pos[slot_key] = st.selectbox(
                "Show Brand Logo at", LOGO_POSITIONS,
                index=LOGO_POSITIONS.index(st.session_state.slot_logo_pos.get(slot_key, "Top")),
                key="logo_pos_kf",
            )

            st.markdown("**4 Key Product Facts**")
            facts = st.session_state.slot_facts.get(slot_key, ["", "", "", ""])
            new_facts = []
            for fi in range(4):
                val = st.text_input(
                    f"Key Fact {fi+1}", value=facts[fi] if fi < len(facts) else "",
                    key=f"kf_{fi}", placeholder=f"Key Fact {fi+1}", label_visibility="collapsed",
                )
                new_facts.append(val)
            st.session_state.slot_facts[slot_key] = new_facts

            has_facts = any(f.strip() for f in new_facts)
            if st.button("🚀 Generate Key Facts Image", key="gen_kf", type="primary",
                         disabled=not has_facts):
                facts_text = "; ".join(f for f in new_facts if f.strip())
                generate_single_image(
                    "key_facts",
                    extra_instructions=(
                        f"Create a product infographic with key facts. "
                        f"Background style: {st.session_state.slot_bg_style.get(slot_key, 'Minimal')}. "
                        f"Show brand logo at: {st.session_state.slot_logo_pos.get(slot_key, 'Top')}. "
                        f"Display these 4 key facts as visual badges or callouts: {facts_text}. "
                        f"Use the main product image as reference."
                    ),
                )
                st.rerun()

            show_preview_refine_download("key_facts", "Key Facts")

        # ========================== IMAGE 3: LIFESTYLE ==========================
        elif slot_key == "lifestyle":
            st.markdown("### Image 3 – Lifestyle Scene")
            st.caption("Upload an additional reference image and describe the scenario.")

            lifestyle_upload = st.file_uploader(
                "Upload additional reference image", type=["png", "jpg", "jpeg"],
                key="upload_lifestyle",
            )
            if lifestyle_upload:
                st.session_state.slot_uploads[slot_key] = lifestyle_upload
                st.image(lifestyle_upload, caption="Reference image", width=300)

            scenario_desc = st.text_area(
                "Scenario Description *",
                placeholder="e.g., A child playing with the product in a bright living room with natural sunlight...",
                key="lifestyle_scenario",
                height=100,
            )

            if st.button("🚀 Generate Lifestyle Image", key="gen_lifestyle", type="primary",
                         disabled=not scenario_desc):
                extra_uploads = [lifestyle_upload] if lifestyle_upload else None
                generate_single_image(
                    "lifestyle",
                    extra_instructions=(
                        f"Create a lifestyle scene: {scenario_desc}. "
                        f"Show the product being used in a realistic setting. "
                        f"Warm, inviting lighting. Professional lifestyle photography."
                    ),
                    input_image_uploads=extra_uploads,
                )
                st.rerun()

            show_preview_refine_download("lifestyle", "Lifestyle")

        # ========================== IMAGE 4: USP HIGHLIGHT ==========================
        elif slot_key == "usps":
            st.markdown(f"### Image {active+1} – USP Highlight Image")
            st.caption("Visual representation of unique selling points")

            st.markdown("**USP Highlights with Icons**")
            usp_items = st.session_state.slot_facts.get("usps", ["", "", "", ""])
            if len(usp_items) < 4:
                usp_items = usp_items + [""] * (4 - len(usp_items))
            new_usps = []
            for ui in range(4):
                val = st.text_input(
                    f"USP Highlight {ui+1}",
                    value=usp_items[ui] if ui < len(usp_items) else "",
                    key=f"usp_input_{ui}",
                    placeholder=f"USP Highlight {ui+1}",
                    label_visibility="collapsed",
                )
                new_usps.append(val)
            st.session_state.slot_facts["usps"] = new_usps

            has_usps = any(u.strip() for u in new_usps)

            # Preview placeholder
            if "usps" not in st.session_state.generated_images:
                st.markdown("""
                <div style="background:#f5f7fa; border-radius:12px; padding:60px 20px; text-align:center; color:#8e99a4; margin:16px 0;">
                    🏅<br>Preview: USP Grid Layout
                </div>
                """, unsafe_allow_html=True)

            if st.button("🚀 Generate Images", key="gen_usp", type="primary", disabled=not has_usps):
                usp_text = "; ".join(u for u in new_usps if u.strip())
                generate_single_image(
                    "usps",
                    extra_instructions=(
                        f"Create a professional USP highlight image. "
                        f"The product must be centered in the composition. "
                        f"Place these EXACT USP callouts around the product with icons: {usp_text}. "
                        f"Each callout must show the EXACT text provided — no paraphrasing. "
                        f"Use brand colors for callout backgrounds. Professional infographic quality."
                    ),
                    emphasis_items=new_usps,
                )
                st.rerun()

            show_preview_refine_download("usps", "USP Highlight")

        # ========================== IMAGE 5: COMPARISON ==========================
        elif slot_key == "comparison":
            st.markdown(f"### Image {active+1} – Comparison Image")
            st.caption("Us vs Other Products comparison")

            # Initialize comparison data
            if "advantages" not in st.session_state:
                st.session_state.advantages = ["", "", ""]
            if "limitations" not in st.session_state:
                st.session_state.limitations = ["", "", ""]

            col_adv, col_lim = st.columns(2)
            with col_adv:
                st.markdown('<span style="color:#22c55e; font-weight:600;">✓ Our Product – Key Advantages</span>', unsafe_allow_html=True)
                new_advs = []
                for ai_idx in range(3):
                    val = st.text_input(
                        f"Advantage {ai_idx+1}", value=st.session_state.advantages[ai_idx],
                        key=f"adv_{ai_idx}", placeholder=f"Advantage {ai_idx+1}", label_visibility="collapsed",
                    )
                    new_advs.append(val)
                st.session_state.advantages = new_advs

            with col_lim:
                st.markdown('<span style="color:#ef4444; font-weight:600;">✗ Other Products – Limitations</span>', unsafe_allow_html=True)
                new_lims = []
                for li_idx in range(3):
                    val = st.text_input(
                        f"Limitation {li_idx+1}", value=st.session_state.limitations[li_idx],
                        key=f"lim_{li_idx}", placeholder=f"Limitation {li_idx+1}", label_visibility="collapsed",
                    )
                    new_lims.append(val)
                st.session_state.limitations = new_lims

            has_comp = any(a.strip() for a in new_advs) or any(l.strip() for l in new_lims)

            # Preview placeholder
            if "comparison" not in st.session_state.generated_images:
                st.markdown("""
                <div style="background:#f5f7fa; border-radius:12px; padding:60px 20px; text-align:center; color:#8e99a4; margin:16px 0;">
                    ⚖️<br>Preview: Comparison Table
                </div>
                """, unsafe_allow_html=True)

            if st.button("🚀 Generate Images", key="gen_comp", type="primary", disabled=not has_comp):
                adv_text = "; ".join(f"✓ {a}" for a in new_advs if a.strip())
                lim_text = "; ".join(f"✗ {l}" for l in new_lims if l.strip())
                all_items = [f"ADV:{a}" for a in new_advs if a.strip()] + [f"LIM:{l}" for l in new_lims if l.strip()]
                generate_single_image(
                    "comparison",
                    extra_instructions=(
                        f"Create a professional comparison infographic. "
                        f"Split the image into TWO halves. "
                        f"LEFT side (green header '✓ Our Product'): list these advantages: {adv_text}. "
                        f"RIGHT side (red header '✗ Others'): list these limitations: {lim_text}. "
                        f"Render the EXACT text provided — no paraphrasing or invented text. "
                        f"Clean, professional layout with clear contrast."
                    ),
                    emphasis_items=all_items,
                )
                st.rerun()

            show_preview_refine_download("comparison", "Comparison")

        # ========================== IMAGE 6: CROSS-SELLING ==========================
        elif slot_key == "cross_selling":
            st.markdown(f"### Image {active+1} – Cross-Selling Image")
            st.caption("Showcase related products for cross-selling")

            st.markdown("**Select Cross-Sell Products**")

            # Initialize cross-sell product names
            if "cross_sell_products" not in st.session_state:
                st.session_state.cross_sell_products = ["", "", "", "", "", ""]

            cs_products = st.session_state.cross_sell_products
            # 3x2 grid layout
            row1 = st.columns(3)
            row2 = st.columns(3)
            new_cs = []
            for ci, col in enumerate(row1):
                with col:
                    st.markdown(f"""
                    <div style="background:#f5f7fa; border:2px solid #e2e8f0; border-radius:12px; padding:30px 10px 10px; text-align:center; color:#8e99a4; margin-bottom:8px;">
                        🛒
                    </div>
                    """, unsafe_allow_html=True)
                    val = st.text_input(
                        f"Product {chr(65+ci)}", value=cs_products[ci] if ci < len(cs_products) else "",
                        key=f"cs_prod_{ci}", placeholder=f"Product {chr(65+ci)}", label_visibility="collapsed",
                    )
                    new_cs.append(val)
            for ci_offset, col in enumerate(row2):
                ci = ci_offset + 3
                with col:
                    st.markdown(f"""
                    <div style="background:#f5f7fa; border:2px solid #e2e8f0; border-radius:12px; padding:30px 10px 10px; text-align:center; color:#8e99a4; margin-bottom:8px;">
                        🛒
                    </div>
                    """, unsafe_allow_html=True)
                    val = st.text_input(
                        f"Product {chr(65+ci)}", value=cs_products[ci] if ci < len(cs_products) else "",
                        key=f"cs_prod_{ci}", placeholder=f"Product {chr(65+ci)}", label_visibility="collapsed",
                    )
                    new_cs.append(val)
            st.session_state.cross_sell_products = new_cs

            has_cs = any(p.strip() for p in new_cs)

            # Preview placeholder
            if "cross_selling" not in st.session_state.generated_images:
                st.markdown("""
                <div style="background:#f5f7fa; border-radius:12px; padding:60px 20px; text-align:center; color:#8e99a4; margin:16px 0;">
                    🛒<br>Preview: Cross-Sell Grid
                </div>
                """, unsafe_allow_html=True)

            if st.button("🚀 Generate Images", key="gen_cs", type="primary", disabled=not has_cs):
                product_names = [p for p in new_cs if p.strip()]
                names_text = ", ".join(product_names)
                generate_single_image(
                    "cross_selling",
                    extra_instructions=(
                        f"Create a cross-selling product grid image. "
                        f"Place the main product LARGER at the top center. "
                        f"Below it, create a 3×2 grid showing these related products: {names_text}. "
                        f"Each grid cell has a product card with the EXACT product name label. "
                        f"Include 'Discover More' or 'Complete Your Collection' at the bottom. "
                        f"Use ONLY the product names provided — do not invent names."
                    ),
                    emphasis_items=product_names,
                )
                st.rerun()

            show_preview_refine_download("cross_selling", "Cross-Selling")

        # ========================== IMAGE 7: CLOSING ==========================
        elif slot_key == "closing":
            st.markdown(f"### Image {active+1} – Closing / Emotional Image")
            st.caption("Final message to inspire action")

            # Direction selection
            st.markdown("**Direction Selection**")
            if "closing_direction" not in st.session_state:
                st.session_state.closing_direction = "Emotional"

            dir_cols = st.columns(3)
            directions = [
                ("❤️", "Emotional"),
                ("✨", "Inspirational"),
                ("🏢", "Brand Storytelling"),
            ]
            for di, col in enumerate(dir_cols):
                with col:
                    is_selected = st.session_state.closing_direction == directions[di][1]
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(
                        f"{directions[di][0]} {directions[di][1]}",
                        key=f"dir_btn_{di}",
                        type=btn_type,
                        use_container_width=True,
                    ):
                        st.session_state.closing_direction = directions[di][1]
                        st.rerun()

            # Custom headline
            st.markdown("**Custom Closing Headline (Optional)**")
            if "closing_headline" not in st.session_state:
                st.session_state.closing_headline = ""
            st.session_state.closing_headline = st.text_input(
                "Closing Headline",
                value=st.session_state.closing_headline,
                key="closing_headline_input",
                placeholder="e.g., Are you ready to expand your world?",
                label_visibility="collapsed",
            )

            # Preview placeholder
            if "closing" not in st.session_state.generated_images:
                st.markdown("""
                <div style="background:#f5f7fa; border-radius:12px; padding:60px 20px; text-align:center; color:#8e99a4; margin:16px 0;">
                    ❤️<br>Preview: Closing Message
                </div>
                """, unsafe_allow_html=True)

            if st.button("🚀 Generate Images", key="gen_cl", type="primary"):
                direction = st.session_state.closing_direction
                headline = st.session_state.closing_headline.strip()
                headline_instruction = f'Render this EXACT headline: "{headline}"' if headline else "No headline text — create a purely visual composition."
                emphasis = [headline] if headline else []
                generate_single_image(
                    "closing",
                    extra_instructions=(
                        f"Create a premium closing image with '{direction}' direction. "
                        f"{headline_instruction} "
                        f"Product displayed beautifully with dramatic composition. "
                        f"Use brand colors prominently. Brand logo visible. "
                        f"Professional brand campaign quality — this is the FINAL impression."
                    ),
                    emphasis_items=emphasis,
                )
                st.rerun()

            show_preview_refine_download("closing", "Closing")

    # --- Back button ---
    st.markdown("---")
    col_l, _, _ = st.columns([1, 2, 1])
    with col_l:
        st.button("← Back", key="back_4", on_click=go_back)


# ------------------------------------------------------------------ #
#  Main application flow                                              #
# ------------------------------------------------------------------ #
inject_css()

# Sidebar
st.sidebar.title("Sina Laut AI")
st.session_state["base_url"] = st.sidebar.text_input("API base URL", DEFAULT_BASE_URL)

page = st.sidebar.radio("Page", ["Generate", "Jobs"], label_visibility="collapsed")

if page == "Jobs":
    st.title("Job Status")
    base_url = get_base_url()
    if st.session_state.job_ids:
        job_id = st.selectbox("Job ID", st.session_state.job_ids)
        if st.button("Refresh job status") and job_id:
            resp = call_api("get", f"{base_url}/step4/jobs/{job_id}")
            if resp.status_code >= 400:
                st.error(f"Error {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                st.write({"status": data.get("status")})
                images = data.get("images") or []
                if images:
                    cols = st.columns(2)
                    for idx, img in enumerate(images):
                        with cols[idx % 2]:
                            st.write(f"### {img.get('slot_name')}")
                            path = img.get("file_path")
                            url = img.get("image_url")
                            if path and pathlib.Path(path).exists():
                                st.image(path, caption=path)
                            elif url:
                                st.image(url, caption=url)
                            st.caption(img.get("prompt", "")[:200] + "...")
                else:
                    st.info("No images yet.")
    else:
        st.info("No jobs submitted yet.")
else:
    # ---- Wizard ----
    step = st.session_state.current_step
    if step < 1:
        st.session_state.current_step = 1
        step = 1
    if step > 4:
        st.session_state.current_step = 4
        step = 4

    render_stepper(step, 4)

    if step == 1:
        step_project_setup()
    elif step == 2:
        step_brand_ci()
    elif step == 3:
        step_product_info()
    elif step == 4:
        step_image_setup()

st.sidebar.markdown("---")
st.sidebar.caption("Run FastAPI: `uvicorn app.main:app --reload`")
st.sidebar.caption("Run Streamlit: `streamlit run streamlit_app.py`")
