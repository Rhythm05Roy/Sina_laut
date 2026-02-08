import json
import pathlib
from typing import Any, Dict, List

import requests
import base64
import streamlit as st

# ---------- Config ----------
st.set_page_config(page_title="Sina Laut AI Tester", layout="wide")
DEFAULT_BASE_URL = "http://127.0.0.1:8000/api"
SLOTS = [
    ("main_product", "Main image (centered)"),
    ("key_facts", "Key facts (4 badges)"),
    ("lifestyle", "Lifestyle"),
    ("usps", "USPs"),
    ("cross_selling", "Cross selling"),
    ("closing", "Closing"),
    ("comparison", "Comparison"),
]

# ---------- Helpers ----------
def call_api(method: str, url: str, **kwargs) -> requests.Response:
    func = getattr(requests, method.lower())
    resp = func(url, **kwargs)
    return resp


def build_payload(project: Dict[str, Any], brand: Dict[str, Any], product: Dict[str, Any], assets: List[Dict[str, str]], briefs: List[Dict[str, Any]], remove_bg: bool) -> Dict[str, Any]:
    return {
        "project": project,
        "brand": brand,
        "product": product,
        "assets": assets,
        "image_briefs": briefs,
        "remove_background": remove_bg,
    }


def render_images(images: List[Dict[str, Any]]):
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
            st.caption(img.get("prompt", ""))


def text_to_list(val: str) -> List[str]:
    return [x.strip() for x in val.split(",") if x.strip()]


def to_data_url(upload) -> str:
    """Convert a Streamlit UploadedFile to a data URL."""
    if upload is None:
        return ""
    mime = upload.type or "application/octet-stream"
    b64 = base64.b64encode(upload.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ---------- State ----------
if "job_ids" not in st.session_state:
    st.session_state.job_ids = []

# ---------- UI ----------
st.sidebar.title("FastAPI Client")
base_url = st.sidebar.text_input("API base URL", DEFAULT_BASE_URL)

st.title("Sina Laut AI - Streamlit Tester")
tabs = st.tabs(["Generate", "Refine", "Jobs"])

# ---------- Generate Tab ----------
with tabs[0]:
    st.subheader("Generate images")
    with st.form("gen_form"):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Project name", "Playmobil Launch")
            brand_name = st.text_input("Brand name", "Playmobil")
            category = st.text_input("Product category", "Toys")
            marketplaces = st.multiselect("Target marketplaces", ["amazon", "google"], default=["amazon"])
        with col2:
            logo_file = st.file_uploader("Brand logo (PNG/JPG/SVG)", type=["png", "jpg", "jpeg", "svg"])
            primary_color = st.text_input("Primary color", "#6366f1")
            secondary_color = st.text_input("Secondary color", "#8b5cf6")
            font_heading = st.text_input("Font heading", "Inter")
            font_body = st.text_input("Font body", "Roboto")

        st.markdown("**Product**")
        sku = st.text_input("SKU", "SKU-12345")
        title = st.text_input("Title", "Cat Cafe Playset")
        short_desc = st.text_area("Short description", "Playset with figures and cafe props")
        usps = text_to_list(st.text_input("USPs (comma separated)", "72 pieces, Great for small hands"))
        kw_primary = text_to_list(st.text_input("Keywords primary (comma separated)", "cat cafe, playset"))
        kw_secondary = text_to_list(st.text_input("Keywords secondary (comma separated)", "kids, toy"))
        languages = st.multiselect("Languages", ["en", "de", "fr", "es", "it", "nl", "pl"], default=["en"])

        st.markdown("**Assets**")
        asset_file = st.file_uploader("Product photo", type=["png", "jpg", "jpeg"])
        remove_bg = st.checkbox("Remove background", value=True)

        st.markdown("**Image briefs**")
        chosen_slots = st.multiselect("Select slots to generate", [s[0] for s in SLOTS], default=[s[0] for s in SLOTS[:3]])
        briefs = []
        for slot in chosen_slots:
            exp = st.expander(f"Brief for {slot}")
            with exp:
                inst = st.text_input(f"Instructions ({slot})", "", key=f"inst_{slot}")
                emphasis = text_to_list(st.text_input(f"Emphasis ({slot})", "", key=f"emp_{slot}"))
                style = st.text_input(f"Style ({slot})", "Playful", key=f"style_{slot}")
            briefs.append({"slot_name": slot, "instructions": inst, "emphasis": emphasis, "style": style})

        submitted = st.form_submit_button("Send /api/ai/generate")
        if submitted:
            project = {
                "project_name": project_name,
                "brand_name": brand_name,
                "product_category": category,
                "target_marketplaces": marketplaces,
            }
            brand = {
                "logo_url": to_data_url(logo_file) or None,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "font_heading": font_heading,
                "font_body": font_body,
            }
            product = {
                "sku": sku,
                "title": title,
                "short_description": short_desc,
                "usps": usps,
                "keywords": {"primary": kw_primary, "secondary": kw_secondary},
                "languages": languages,
            }
            asset_url = to_data_url(asset_file)
            assets = [{"type": "product_photo", "url": asset_url}] if asset_url else []
            payload = build_payload(project, brand, product, assets, briefs, remove_bg)
            resp = call_api("post", f"{base_url}/ai/generate", json=payload)
            if resp.status_code >= 400:
                st.error(f"Error {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                job_id = data.get("job_id")
                if job_id:
                    st.session_state.job_ids.append(job_id)
                st.success(f"Queued job: {job_id}")

# ---------- Refine Tab ----------
with tabs[1]:
    st.subheader("Refine with feedback")
    with st.form("refine_form"):
        feedback = st.text_input("Feedback (e.g., 'more premium look, focus on outdoor usage')", "more premium look")
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Project name ", "Playmobil Launch", key="ref_proj")
            brand_name = st.text_input("Brand name ", "Playmobil", key="ref_brand")
            category = st.text_input("Product category ", "Toys", key="ref_cat")
            marketplaces = st.multiselect("Target marketplaces ", ["amazon", "google"], default=["amazon"], key="ref_mkt")
        with col2:
            logo_file = st.file_uploader("Brand logo (PNG/JPG/SVG) ", type=["png", "jpg", "jpeg", "svg"], key="ref_logo")
            primary_color = st.text_input("Primary color ", "#6366f1", key="ref_pc")
            secondary_color = st.text_input("Secondary color ", "#8b5cf6", key="ref_sc")
            font_heading = st.text_input("Font heading ", "Inter", key="ref_fh")
            font_body = st.text_input("Font body ", "Roboto", key="ref_fb")

        sku = st.text_input("SKU ", "SKU-12345", key="ref_sku")
        title = st.text_input("Title ", "Cat Cafe Playset", key="ref_title")
        short_desc = st.text_area("Short description ", "Playset with figures and cafe props", key="ref_sd")
        usps = text_to_list(st.text_input("USPs (comma separated) ", "72 pieces, Great for small hands", key="ref_usps"))
        kw_primary = text_to_list(st.text_input("Keywords primary (comma separated) ", "cat cafe, playset", key="ref_kp"))
        kw_secondary = text_to_list(st.text_input("Keywords secondary (comma separated) ", "kids, toy", key="ref_ks"))
        languages = st.multiselect("Languages ", ["en", "de", "fr", "es", "it", "nl", "pl"], default=["en"], key="ref_lang")

        asset_file = st.file_uploader("Product photo ", type=["png", "jpg", "jpeg"], key="ref_asset")
        remove_bg = st.checkbox("Remove background ", value=True, key="ref_bg")

        chosen_slots = st.multiselect("Select slots to generate ", [s[0] for s in SLOTS], default=[s[0] for s in SLOTS[:3]], key="ref_slots")
        briefs = []
        for slot in chosen_slots:
            exp = st.expander(f"Brief for {slot} ")
            with exp:
                inst = st.text_input(f"Instructions ({slot}) ", "", key=f"ref_inst_{slot}")
                emphasis = text_to_list(st.text_input(f"Emphasis ({slot}) ", "", key=f"ref_emp_{slot}"))
                style = st.text_input(f"Style ({slot}) ", "Playful", key=f"ref_style_{slot}")
            briefs.append({"slot_name": slot, "instructions": inst, "emphasis": emphasis, "style": style})

        submitted = st.form_submit_button("Send /api/ai/refine")
        if submitted:
            project = {
                "project_name": project_name,
                "brand_name": brand_name,
                "product_category": category,
                "target_marketplaces": marketplaces,
            }
            brand = {
                "logo_url": to_data_url(logo_file) or None,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "font_heading": font_heading,
                "font_body": font_body,
            }
            product = {
                "sku": sku,
                "title": title,
                "short_description": short_desc,
                "usps": usps,
                "keywords": {"primary": kw_primary, "secondary": kw_secondary},
                "languages": languages,
            }
            asset_url = to_data_url(asset_file)
            assets = [{"type": "product_photo", "url": asset_url}] if asset_url else []
            payload = build_payload(project, brand, product, assets, briefs, remove_bg)
            body = {"feedback": feedback, "request": payload}
            resp = call_api("post", f"{base_url}/ai/refine", json=body)
            if resp.status_code >= 400:
                st.error(f"Error {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                job_id = data.get("job_id")
                if job_id:
                    st.session_state.job_ids.append(job_id)
                st.success(f"Refine queued: {job_id}")

# ---------- Jobs Tab ----------
with tabs[2]:
    st.subheader("Job status")
    job_id = st.selectbox("Job ID", st.session_state.job_ids)
    if st.button("Refresh job status") and job_id:
        resp = call_api("get", f"{base_url}/ai/jobs/{job_id}")
        if resp.status_code >= 400:
            st.error(f"Error {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            st.write({"status": data.get("status")})
            images = data.get("images") or []
            if images:
                render_images(images)
            else:
                st.info("No images yet.")

st.sidebar.markdown("---")
st.sidebar.write("1) Run FastAPI: `uvicorn app.main:app --reload`\n2) Run Streamlit: `streamlit run streamlit_app.py`")
