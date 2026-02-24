from __future__ import annotations
import base64
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

# ── Marketplace-specific DataForSEO endpoints ──────────────────────────────
ENDPOINTS: Dict[str, str] = {
    # Amazon keyword search volume (direct marketplace data)
    "amazon": "https://api.dataforseo.com/v3/keywords_data/amazon/search_volume/live",
    # Google Shopping – best proxy for Google marketplace
    "google_shopping": "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live",
    # eBay / Walmart / generic – fall back to Google Ads keyword expansion
    "default": "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live",
}

# Amazon location codes: https://docs.dataforseo.com/v3/keywords_data/amazon/
AMAZON_LOCATION_CODES: Dict[str, int] = {
    "United States": 2840,
    "United Kingdom": 2826,
    "Germany": 2276,
    "France": 2250,
    "Canada": 2124,
    "Australia": 2036,
}


class DataForSEOClient:
    def __init__(self, settings: Settings):
        self.login = settings.dataforseo_login
        self.password = settings.dataforseo_password
        self.enabled = bool(self.login and self.password)

    def _auth_header(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.login}:{self.password}".encode("utf-8")).decode("ascii")
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def _get_endpoint(self, marketplace: str) -> str:
        """Return the correct DataForSEO endpoint for the target marketplace."""
        key = marketplace.lower().replace(" ", "_")
        return ENDPOINTS.get(key, ENDPOINTS["default"])

    async def fetch_keywords(
        self,
        seeds: List[str],
        marketplace: str = "amazon",
        language: str = "en",
        location_name: str = "United States",
    ) -> List[Dict[str, Any]]:
        """
        Fetch marketplace keywords from DataForSEO.

        Returns a list of dicts:
            {"keyword": str, "search_volume": int, "competition": float}

        Falls back to [] if API is disabled or fails.
        """
        if not self.enabled:
            logger.info("DataForSEO disabled — no credentials configured.")
            return []

        endpoint = self._get_endpoint(marketplace)
        clean_seeds = [s for s in seeds if s and len(s) <= 80][:10]  # API max & cost control
        if not clean_seeds:
            return []

        # ── Build task payload based on marketplace ──────────────────────
        if marketplace.lower() == "amazon":
            location_code = AMAZON_LOCATION_CODES.get(location_name, 2840)
            task = {
                "location_code": location_code,
                "language_code": language,
                "keywords": clean_seeds,
            }
        else:
            task = {
                "language_name": "English",
                "location_name": location_name,
                "keywords": clean_seeds,
            }

        payload = [task]
        headers = self._auth_header()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)

            if resp.status_code != 200:
                logger.warning(
                    "DataForSEO HTTP %s for marketplace=%s: %s",
                    resp.status_code, marketplace, resp.text[:400],
                )
                return []

            data = resp.json()
            results: List[Dict[str, Any]] = []

            for task_item in data.get("tasks", []):
                task_result = task_item.get("result") or []
                for r in task_result:
                    # Amazon endpoint returns items directly; Google returns nested keywords
                    items = r.get("items") or r.get("keywords") or []
                    for item in items:
                        if isinstance(item, str):
                            results.append({"keyword": item, "search_volume": 0, "competition": 0.5})
                        elif isinstance(item, dict):
                            kw = item.get("keyword") or item.get("keyword_data", {}).get("keyword", "")
                            sv = (
                                item.get("search_volume")
                                or item.get("keyword_data", {}).get("keyword_info", {}).get("search_volume", 0)
                                or 0
                            )
                            comp = (
                                item.get("competition")
                                or item.get("keyword_data", {}).get("keyword_info", {}).get("competition", 0.5)
                                or 0.5
                            )
                            if kw:
                                results.append({
                                    "keyword": str(kw),
                                    "search_volume": int(sv),
                                    "competition": float(comp),
                                })

            logger.info(
                "DataForSEO returned %d keyword results for marketplace=%s",
                len(results), marketplace,
            )
            return results

        except Exception as exc:
            logger.warning("DataForSEO fetch failed (marketplace=%s): %s", marketplace, exc)
            return []
