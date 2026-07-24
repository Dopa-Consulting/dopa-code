from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from inti.openrouter_client import openrouter, OPENROUTER_MODELS

router = APIRouter()


@router.get("/health")
async def check_health():
    if not openrouter.is_configured:
        return {"status": "not_configured", "message": "DOPA_OPENROUTER_API_KEY no configurada"}
    credits = await openrouter.check_credits()
    return {
        "status": "ok" if "credits_remaining" in credits else "error",
        "credits": credits,
    }


@router.get("/models")
async def list_models():
    if not openrouter.is_configured:
        return {
            "models": [
                {"id": mid, **info} for mid, info in OPENROUTER_MODELS.items()
            ],
            "source": "cached",
        }
    models = await openrouter.list_models()
    return {"models": models, "total": len(models)}


@router.get("/models/catalog")
async def model_catalog():
    return {
        "catalog": [
            {
                "id": mid,
                "name": info["name"],
                "provider": info["provider"],
                "context_length": info["context_length"],
                "max_output": info["max_output"],
                "pricing_per_1m_tokens": info["pricing"],
                "capabilities": info["capabilities"],
            }
            for mid, info in OPENROUTER_MODELS.items()
        ]
    }


@router.post("/chat/test")
async def test_chat(
    model: str = "deepseek/deepseek-chat",
    prompt: str = "Say hello in one sentence.",
):
    if not openrouter.is_configured:
        return {"error": "DOPA_OPENROUTER_API_KEY no configurada"}
    result = await openrouter.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )
    return result


@router.post("/chat/stream")
async def chat_stream(
    model: str = "deepseek/deepseek-chat",
    prompt: str = "Say hello in one sentence.",
):
    if not openrouter.is_configured:
        return StreamingResponse(
            iter([b'data: {"error": "API key not configured"}\n\n']),
            media_type="text/event-stream",
        )

    async def event_stream():
        async for chunk in openrouter.chat_stream(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        ):
            import json
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/config")
async def configure_key(api_key: str):
    await openrouter.save_key(api_key)
    credits = await openrouter.check_credits()
    return {
        "status": "configured" if "credits_remaining" in credits else "invalid_key",
        "credits": credits,
        "persisted": True,
    }


@router.get("/cost-estimate")
async def estimate_cost(
    model: str = Query("deepseek/deepseek-chat"),
    prompt_tokens: int = Query(1000),
    completion_tokens: int = Query(500),
):
    cost = openrouter._estimate_cost(model, prompt_tokens, completion_tokens)
    return {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost": cost,
    }


# --- Multi-Provider Direct APIs ---

from inti.openrouter_client import multiprovider, PROVIDER_ENDPOINTS


@router.post("/provider/config")
async def configure_provider(provider: str, api_key: str):
    if provider not in PROVIDER_ENDPOINTS:
        return {"error": f"Provider no soportado: {provider}. Usa: {list(PROVIDER_ENDPOINTS.keys())}"}
    await multiprovider.configure(provider, api_key)
    return {"status": "ok", "provider": provider, "message": f"API key configurada para {provider}"}


@router.get("/provider/status")
async def provider_status():
    return {
        "providers": [
            {
                "name": p,
                "endpoint": PROVIDER_ENDPOINTS[p],
                "configured": multiprovider.is_configured(p),
            }
            for p in PROVIDER_ENDPOINTS
        ]
    }


@router.post("/provider/chat")
async def direct_chat(
    provider: str = "deepseek",
    model: str = "deepseek-chat",
    prompt: str = "Say hello in one sentence.",
):
    result = await multiprovider.chat(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )
    return result


# --- Image Generation (Nano Banana via Google AI) ---


@router.post("/image/generate")
async def generate_image(
    prompt: str,
    model: str = "nano-banana-2",
    aspect_ratio: str = "1:1",
    num_images: int = 1,
):
    api_key = multiprovider.providers.get("google") or settings.google_api_key
    if not api_key:
        return {"error": "Google API key not configured"}

    if settings.dopa_code_dummy:
        return {"images": [{"url": f"https://dummy.dopa.dev/img/{i}.png"} for i in range(num_images)], "model": model}

    model_map = {
        "nano-banana-2": "gemini-3.1-flash-image",
        "nano-banana-2-lite": "gemini-3.1-flash-lite-image",
        "nano-banana-pro": "gemini-3-pro-image",
        "nano-banana": "gemini-2.5-flash-image",
    }
    gemini_model = model_map.get(model, "gemini-3.1-flash-image")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{gemini_model}:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
                },
            )
            if resp.status_code != 200:
                return {"error": f"Image gen failed ({resp.status_code})", "detail": resp.text[:500]}
            data = resp.json()
            images = []
            for c in data.get("candidates", []):
                for p in c.get("content", {}).get("parts", []):
                    if "inlineData" in p:
                        images.append({"mime_type": p["inlineData"].get("mimeType"), "data_length": len(p["inlineData"].get("data", ""))})
                    if "text" in p:
                        images.append({"description": p["text"]})
            return {"images": images, "model": gemini_model, "prompt": prompt}
    except Exception as e:
        return {"error": str(e)}
