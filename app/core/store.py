"""
Shared in-memory store for Wizard steps.
Stores Project, Brand, and Product data to allow stateful step-by-step API usage.
"""
from typing import Dict, Any, List

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
