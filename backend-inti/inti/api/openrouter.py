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
    openrouter.api_key = api_key
    credits = await openrouter.check_credits()
    return {
        "status": "configured" if "credits_remaining" in credits else "invalid_key",
        "credits": credits,
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
    multiprovider.configure(provider, api_key)
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
