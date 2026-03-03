"""
Shared in-memory store for Wizard steps.
Stores Project, Brand, and Product data to allow stateful step-by-step API usage.
"""
from typing import Dict, Any, List, Optional

# Global dictionaries to simulate a database.
# In a real production app, use Redis or SQL.

projects: Dict[str, Any] = {}
brands: Dict[str, Any] = {}
products: Dict[str, Any] = {}

# Store for assets (e.g. uploaded main product) and generated images.
# Structure: { project_id: { "main_product": "http...", "key_facts": "http..." } }
generated_images: Dict[str, Dict[str, str]] = {}

# Structure: { project_id: { "main_raw": "http...", "lifestyle_ref": "http..." } }
assets: Dict[str, Dict[str, str]] = {}

# Optional per-project defaults supplied in main-product route.
# Structure:
# {
#   project_id: {
#     "generate": {slot_name: {...}},
#     "refine": {slot_name: {...}}
#   }
# }
project_slot_defaults: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}

# Step 4 generation context memory.
# context_id -> project_id
generation_contexts: Dict[str, str] = {}
# job_id -> context_id
job_contexts: Dict[str, str] = {}
# Latest context used (single-instance convenience for local testing)
latest_context_id: Optional[str] = None

def get_brand_by_project_id(project_id: str) -> dict | None:
    for brand in brands.values():
        if brand.get("project_id") == project_id:
            return brand
    return None

def get_product_by_project_id(project_id: str) -> dict | None:
    for product in products.values():
        if product.get("project_id") == project_id:
            return product
    return None

def get_generated_image_url(project_id: str, slot_name: str) -> str | None:
    """Retrieve URL of a previously generated image for context."""
    if project_id in generated_images:
        return generated_images[project_id].get(slot_name)
    return None

def save_generated_image_url(project_id: str, slot_name: str, url: str):
    """Save generated image URL for future context."""
    if project_id not in generated_images:
        generated_images[project_id] = {}
    generated_images[project_id][slot_name] = url

def save_asset_url(project_id: str, asset_key: str, url: str):
    """Save uploaded asset URL."""
    if project_id not in assets:
        assets[project_id] = {}
    assets[project_id][asset_key] = url

def get_asset_url(project_id: str, asset_key: str) -> str | None:
    """Retrieve uploaded asset URL."""
    if project_id in assets:
        return assets[project_id].get(asset_key)
    return None

def save_generation_context(context_id: str, project_id: str):
    """Persist mapping from context to project for Step 4 follow-up calls."""
    global latest_context_id
    generation_contexts[context_id] = project_id
    latest_context_id = context_id

def get_project_id_by_context(context_id: str) -> str | None:
    return generation_contexts.get(context_id)

def get_latest_context_id() -> str | None:
    return latest_context_id

def bind_job_to_context(job_id: str, context_id: str):
    job_contexts[job_id] = context_id

def get_context_id_by_job(job_id: str) -> str | None:
    return job_contexts.get(job_id)

def save_project_slot_defaults(project_id: str, stage: str, slot_name: str, values: Dict[str, Any]):
    if project_id not in project_slot_defaults:
        project_slot_defaults[project_id] = {"generate": {}, "refine": {}}
    if stage not in project_slot_defaults[project_id]:
        project_slot_defaults[project_id][stage] = {}
    project_slot_defaults[project_id][stage][slot_name] = values

def get_project_slot_defaults(project_id: str, stage: str, slot_name: str) -> Dict[str, Any]:
    return project_slot_defaults.get(project_id, {}).get(stage, {}).get(slot_name, {})
