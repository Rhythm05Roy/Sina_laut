from __future__ import annotations

import sys

import httpx

from app.core.config import get_settings


def test_gemini(settings) -> bool:
    api_key = settings.gemini_text_api_key
    if not api_key:
        print("GEMINI_API_KEY/NANO_BANANA_API_KEY is missing.")
        return False

    base_url = str(settings.gemini_base_url).rstrip("/")
    url = f"{base_url}/models"
    print(f"[Gemini] Listing models via {url} ...")
    try:
        resp = httpx.get(url, params={"key": api_key, "pageSize": 5}, timeout=15)
    except Exception as exc:
        print(f"[Gemini] Request failed: {exc}")
        return False

    if resp.status_code == 200:
        models = [m.get("name") for m in resp.json().get("models", [])]
        print("[Gemini] OK")
        for model in models:
            print(f" - {model}")
        return True

    print(f"[Gemini] FAILED (HTTP {resp.status_code})")
    print(resp.text[:1200])
    return False


def test_openai(settings) -> bool:
    api_key = settings.openai_api_key
    if not api_key:
        print("OPENAI_API_KEY is missing.")
        return False

    base_url = str(settings.openai_base_url).rstrip("/")
    models_to_check = [settings.openai_image_model, settings.openai_analysis_model]
    ok = True

    for model in models_to_check:
        url = f"{base_url}/models/{model}"
        print(f"[OpenAI] Retrieving model via {url} ...")
        try:
            resp = httpx.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
        except Exception as exc:
            print(f"[OpenAI] Request failed for {model}: {exc}")
            ok = False
            continue

        if resp.status_code == 200:
            data = resp.json()
            print(f"[OpenAI] OK - {data.get('id', model)}")
        else:
            ok = False
            print(f"[OpenAI] FAILED for {model} (HTTP {resp.status_code})")
            print(resp.text[:1200])

    return ok


def main() -> None:
    settings = get_settings()
    gemini_ok = test_gemini(settings)
    openai_ok = test_openai(settings)

    print("\nSummary:")
    print(f" - Gemini: {'OK' if gemini_ok else 'FAILED'}")
    print(f" - OpenAI: {'OK' if openai_ok else 'FAILED'}")

    if not (gemini_ok and openai_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
