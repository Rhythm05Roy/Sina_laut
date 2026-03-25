from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    schema = client.get("/api/openapi.json", timeout=30).json()

    main_generate = schema["paths"]["/api/step4/generate/main-product"]["post"]
    key_facts_generate = schema["paths"]["/api/step4/generate/key-facts"]["post"]
    refine_key_facts = schema["paths"]["/api/step4/refine/key-facts"]["post"]

    assert "requestBody" in main_generate, "main-product must accept a request body"
    assert "requestBody" not in key_facts_generate, "key-facts generate route must not require a body"
    assert "requestBody" in refine_key_facts, "refine key-facts must accept a request body"

    response_schema = schema["components"]["schemas"]["GenerationResponse"]["properties"]
    for field in [
        "job_id",
        "status",
        "imageUrl",
        "imageBuffer",
        "imageMimeType",
        "imageFileName",
        "prompt",
        "refinePrompt",
        "rawResponse",
        "analysis_used",
        "analysis_ok",
        "analysis_text",
        "error",
    ]:
        assert field in response_schema, f"GenerationResponse missing field: {field}"

    print("API CONTRACT OK")


if __name__ == "__main__":
    main()
