from __future__ import annotations
from typing import Dict, List
from app.schemas.product import ProductInfo

# Outputs primary and secondary keyword lists
async def crawl_keywords(product: ProductInfo) -> Dict[str, List[str]]:
    base = [product.title, product.short_description]
    usps = product.usps[:4]
    primary = [kw for kw in (product.keywords.get("primary") or [])]
    secondary = [kw for kw in (product.keywords.get("secondary") or [])]

    # simple enrichment stub
    primary += base[:2] + usps
    secondary += base[1:2] + product.languages

    # de-dup and trim
    def uniq(seq):
        seen = set()
        out = []
        for item in seq:
            if item and item.lower() not in seen:
                seen.add(item.lower())
                out.append(item)
        return out

    return {
        "primary": uniq(primary)[:5],
        "secondary": uniq(secondary)[:8],
    }
