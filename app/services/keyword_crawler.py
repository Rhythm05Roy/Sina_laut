from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.schemas.product import ProductInfo
from app.services.dataforseo_client import DataForSEOClient

GENERIC_BAN = {
    "high quality",
    "premium looking",
    "attractive design",
    "nice design",
    "good quality",
}

INTENT_TERMS = ["buy", "best", "price", "deal", "offer", "cheap", "discount"]

VISUAL_TERMS = [
    "color",
    "blue",
    "black",
    "white",
    "red",
    "green",
    "mesh",
    "leather",
    "metal",
    "glass",
    "matte",
    "glossy",
    "lightweight",
    "breathable",
    "cushioned",
    "textured",
]


def _normalize(term: str) -> str:
    return " ".join(term.strip().split()).lower()


_cache: Dict[Tuple[str, str, str, Tuple[str, ...]], Dict[str, List[str]]] = {}


async def crawl_keywords(
    product: ProductInfo,
    category: Optional[str] = None,
    marketplace: str = "amazon",
    analysis: Optional[Dict] = None,
) -> Dict[str, List[str]]:
    """
    Deterministic keyword discovery + scoring with optional DataForSEO enrichment.
    Returns primary, secondary, and clean_visual lists.
    """
    cache_key = (
        (product.title or "").lower(),
        (product.short_description or "").lower(),
        (category or "").lower(),
        tuple((product.usps or [])[:4]),
    )
    if cache_key in _cache:
        return _cache[cache_key]

    cat = (category or "").lower()
    title = product.title or ""
    desc = product.short_description or ""
    usps = product.usps or []

    seeds: List[str] = []
    seeds += [title, desc]
    seeds += usps
    if cat:
        seeds.append(cat)

    for intent in INTENT_TERMS:
        if title:
            seeds.append(f"{intent} {title}")
        if cat:
            seeds.append(f"{intent} {cat}")

    if analysis:
        for key in ["visual_style", "composition", "lighting"]:
            value = analysis.get(key)
            if value:
                seeds.append(value)

    # Flatten to deterministic 1-3 word candidates
    raw_candidates: List[str] = []
    for seed in seeds:
        if not seed:
            continue
        parts = [p.strip() for p in seed.replace(",", " ").split() if p.strip()]
        if len(parts) == 1:
            raw_candidates.append(parts[0])
        else:
            raw_candidates.append(" ".join(parts[:2]))
            raw_candidates.append(" ".join(parts[:3]) if len(parts) >= 3 else " ".join(parts[:2]))

    # Optional DataForSEO enrichment
    settings = get_settings()
    dataforseo = DataForSEOClient(settings)
    dfs_keywords: List[str] = []
    if dataforseo.enabled:
        dfs_keywords = await dataforseo.fetch_keywords(raw_candidates)

    merged_candidates = raw_candidates + [k for k in dfs_keywords if k]

    # De-duplicate and remove blocked generic terms unless user explicitly provided them in USP.
    usp_norm = {u.lower() for u in usps}
    seen = set()
    uniq_candidates: List[str] = []
    for candidate in merged_candidates:
        norm = _normalize(candidate)
        if not norm or norm in seen:
            continue
        if norm in GENERIC_BAN and norm not in usp_norm:
            continue
        seen.add(norm)
        uniq_candidates.append(norm)

    def score(term: str) -> float:
        term_l = term.lower()
        relevance = 1.0 if (cat and cat in term_l) or (title and title.lower().split()[0] in term_l) else 0.6
        # Penalize direct purchase-intent wording for on-image copy.
        intent = 0.2 if any(t in term_l for t in INTENT_TERMS) else 0.8
        category_align = 1.0 if cat and cat in term_l else 0.4
        visual = 1.2 if any(v in term_l for v in VISUAL_TERMS) else 0.2
        return 0.40 * relevance + 0.20 * intent + 0.25 * category_align + 0.15 * visual

    scored = sorted(((term, score(term)) for term in uniq_candidates), key=lambda item: (-item[1], item[0]))

    primary = [term for term, _ in scored[:5]]
    secondary = [term for term, _ in scored[5:13]]
    clean_visual = [term for term, s in scored if s >= 0.6 and term not in GENERIC_BAN]

    result = {
        "primary": primary,
        "secondary": secondary,
        "clean_visual": clean_visual,
    }
    _cache[cache_key] = result
    return result
