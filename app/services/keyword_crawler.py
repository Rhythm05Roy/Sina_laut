from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.schemas.product import ProductInfo
from app.services.gemini_text_client import GeminiTextClient
from app.services.pipeline_models import KeywordPlan

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


_cache: Dict[Tuple[str, str, str, Tuple[str, ...]], KeywordPlan] = {}


async def _gemini_keyword_suggestions(
    product: ProductInfo,
    category: str,
    marketplace: str,
    analysis: Optional[Dict],
    seed_candidates: List[str],
) -> Dict[str, List[str]]:
    settings = get_settings()
    client = GeminiTextClient(settings)
    if not client.api_key:
        return {}

    analysis_text = ""
    if analysis:
        analysis_text = (
            f"Visual style: {analysis.get('visual_style', '')}\n"
            f"Lighting: {analysis.get('lighting', '')}\n"
            f"Composition: {analysis.get('composition', '')}\n"
        )

    system_prompt = (
        "You are a marketplace keyword strategist. "
        "Return only marketplace-relevant, high-intent keywords that are also usable for professional image text. "
        "Avoid generic fluff. Avoid repetitive near-duplicates."
    )
    user_prompt = (
        f"Product title: {product.title}\n"
        f"Category: {category or 'general'}\n"
        f"Marketplace: {marketplace}\n"
        f"USPs: {', '.join(product.usps) if product.usps else 'n/a'}\n"
        f"Description: {product.short_description}\n"
        f"Analysis context:\n{analysis_text or 'n/a'}\n"
        f"Seed candidates: {', '.join(seed_candidates[:25]) if seed_candidates else 'n/a'}\n"
        "Return strict JSON with keys primary, secondary, clean_visual. "
        "primary must have 3-5 items, secondary 5-8 items, clean_visual 4-8 items. "
        "Use short phrases only."
    )
    result = await client.generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_output_tokens=350,
    )
    if not isinstance(result, dict):
        return {}
    return {
        'primary': [str(v) for v in result.get('primary', []) if v],
        'secondary': [str(v) for v in result.get('secondary', []) if v],
        'clean_visual': [str(v) for v in result.get('clean_visual', []) if v],
    }


async def crawl_keywords(
    product: ProductInfo,
    category: Optional[str] = None,
    marketplace: str = "amazon",
    analysis: Optional[Dict] = None,
) -> KeywordPlan:
    """
    Keyword discovery + scoring with Gemini keyword selection and deterministic fallback.
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
                seeds.append(str(value))

    raw_candidates: List[str] = []
    for seed in seeds:
        if not seed:
            continue
        parts = [p.strip() for p in str(seed).replace(',', ' ').split() if p.strip()]
        if len(parts) == 1:
            raw_candidates.append(parts[0])
        else:
            raw_candidates.append(' '.join(parts[:2]))
            raw_candidates.append(' '.join(parts[:3]) if len(parts) >= 3 else ' '.join(parts[:2]))

    merged_candidates = raw_candidates

    usp_norm = {u.lower() for u in usps}
    seen = set()
    uniq_candidates: List[str] = []
    for candidate in merged_candidates:
        norm = _normalize(str(candidate))
        if not norm or norm in seen:
            continue
        if norm in GENERIC_BAN and norm not in usp_norm:
            continue
        seen.add(norm)
        uniq_candidates.append(norm)

    def score(term: str) -> float:
        term_l = term.lower()
        relevance = 1.0 if (cat and cat in term_l) or (title and title.lower().split()[0] in term_l) else 0.6
        intent = 0.1 if any(t in term_l for t in INTENT_TERMS) else 0.9
        category_align = 1.0 if cat and cat in term_l else 0.4
        visual = 1.2 if any(v in term_l for v in VISUAL_TERMS) else 0.2
        return 0.40 * relevance + 0.20 * intent + 0.25 * category_align + 0.15 * visual

    scored = sorted(((term, score(term)) for term in uniq_candidates), key=lambda item: (-item[1], item[0]))

    non_intent_scored = [term for term, _ in scored if not any(t in term for t in INTENT_TERMS)]
    intent_scored = [term for term, _ in scored if any(t in term for t in INTENT_TERMS)]

    fallback_primary = (non_intent_scored + intent_scored)[:5]
    fallback_secondary = [term for term, _ in scored if term not in fallback_primary][:8]
    fallback_clean_visual = [
        term for term, s in scored
        if s >= 0.6 and term not in GENERIC_BAN and not any(t in term for t in INTENT_TERMS)
    ][:8]

    gemini_result = await _gemini_keyword_suggestions(
        product=product,
        category=category or '',
        marketplace=marketplace,
        analysis=analysis,
        seed_candidates=uniq_candidates,
    )

    def _clean_list(values: List[str], fallback: List[str], minimum: int, maximum: int) -> List[str]:
        cleaned: List[str] = []
        for value in values + fallback:
            norm = _normalize(str(value))
            if not norm or norm in GENERIC_BAN or norm in cleaned:
                continue
            cleaned.append(norm)
            if len(cleaned) >= maximum:
                break
        return cleaned[:maximum] if len(cleaned) >= minimum else cleaned + [v for v in fallback if v not in cleaned][: max(0, minimum - len(cleaned))]

    gemini_primary = _clean_list(gemini_result.get('primary', []), [], 0, 5)
    gemini_secondary = _clean_list(gemini_result.get('secondary', []), [], 0, 8)
    gemini_visual = _clean_list(gemini_result.get('clean_visual', []), [], 0, 8)

    fallback_primary_clean = _clean_list([], fallback_primary, 3, 5)
    fallback_secondary_clean = _clean_list([], fallback_secondary, 5, 8)
    fallback_visual_clean = _clean_list([], fallback_clean_visual, 4, 8)

    if gemini_primary or gemini_visual:
        result = KeywordPlan(
            available=True,
            source="gemini",
            primary=gemini_primary or fallback_primary_clean,
            secondary=gemini_secondary or fallback_secondary_clean,
            clean_visual=gemini_visual or fallback_visual_clean,
            warning=None if gemini_result else "Gemini keyword result was partial; supplemented with deterministic fallback.",
        )
    elif fallback_visual_clean or fallback_primary_clean:
        result = KeywordPlan(
            available=True,
            source="fallback",
            primary=fallback_primary_clean,
            secondary=fallback_secondary_clean,
            clean_visual=fallback_visual_clean,
            warning="Gemini keywords unavailable. Using deterministic keyword fallback.",
        )
    else:
        result = KeywordPlan(
            available=False,
            source="none",
            primary=[],
            secondary=[],
            clean_visual=[],
            warning="No verified keyword source available. Text overlays should be skipped.",
        )
    _cache[cache_key] = result
    return result
