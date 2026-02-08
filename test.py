from __future__ import annotations

import sys
from pathlib import Path

import httpx

from app.core.config import get_settings


def main() -> None:
    """Quick check that the Nano Banana API key is accepted."""
    settings = get_settings()
    api_key = settings.nano_banana_api_key

    if not api_key:
        print("NANO_BANANA_API_KEY is missing. Set it in .env first.")
        sys.exit(1)

    base_url = str(settings.nano_banana_base_url).rstrip("/")
    url = f"{base_url}/models"

    print(f"Listing models via {url} ...")
    try:
        resp = httpx.get(url, params={"key": api_key, "pageSize": 5}, timeout=15)
    except Exception as exc:
        print(f"Request failed: {exc}")
        sys.exit(1)

    if resp.status_code == 200:
        models = [m.get("name") for m in resp.json().get("models", [])]
        if models:
            print("✅ API key works. Returned models:")
            for m in models:
                print(f" - {m}")
        else:
            print("✅ API key works, but no models returned.")
        return

    print(f"❌ API call failed (HTTP {resp.status_code}).")
    print(resp.text[:1200])
    sys.exit(1)


if __name__ == "__main__":
    main()
