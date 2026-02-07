from __future__ import annotations
from typing import Dict, List
from app.schemas.product import ProductInfo

DEFAULT_MARKETPLACES = ["amazon", "google"]

async def crawl_keywords(product: ProductInfo) -> Dict[str, List[str]]:
    """Stub keyword crawler; merge existing keywords and enrich with basics.

    Replace with real marketplace crawling (ScraperAPI, SerpAPI, Rainforest API, etc.).
    """
    merged: Dict[str, List[str]] = {m: list(v) for m, v in product.keywords.items()}
    for marketplace in DEFAULT_MARKETPLACES:
        merged.setdefault(marketplace, [])
        merged[marketplace] += [product.title, product.short_description]
        merged[marketplace] = [kw for kw in merged[marketplace] if kw]
    return merged
