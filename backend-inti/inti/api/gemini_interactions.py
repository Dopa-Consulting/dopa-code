from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from inti.gemini_interactions import gemini_interactions, INTERACTIONS_MODELS
from inti.config import settings

router = APIRouter()


@router.get("/models")
async def list_interactions_models():
    return {"models": [
        {"id": mid, **info} for mid, info in INTERACTIONS_MODELS.items()
    ]}


@router.post("/chat")
async def interact(
    model: str = "gemini-2.5-flash",
    user_input: str = "Hello",
    system_instruction: str | None = None,
    background: bool = False,
):
    if not gemini_interactions.is_configured:
        return {"error": "DOPA_GOOGLE_API_KEY not configured"}
    result = await gemini_interactions.interact(
        model=model,
        user_input=user_input,
        system_instruction=system_instruction,
        background=background,
    )
    return result


@router.post("/continue")
async def continue_chat(
    model: str = "gemini-2.5-flash",
    user_input: str = "Continue",
    previous_interaction_id: str | None = None,
):
    if not settings.dopa_code_dummy:
        return await gemini_interactions.continue_interaction(
            model=model,
            user_input=user_input,
            previous_interaction_id=previous_interaction_id,
        )
    return {"status": "dummy", "message": f"Would continue: {user_input[:50]}"}


@router.post("/deep-research")
async def deep_research(query: str, max_mode: bool = False):
    if not gemini_interactions.is_configured:
        return {"error": "DOPA_GOOGLE_API_KEY not configured"}
    result = await gemini_interactions.deep_research(query, max_mode)
    return result


@router.post("/antigravity-qa")
async def antigravity_qa(code_or_diff: str, context: str = ""):
    if not gemini_interactions.is_configured:
        return {"error": "DOPA_GOOGLE_API_KEY not configured"}
    result = await gemini_interactions.antigravity_qa(code_or_diff, context)
    return result


@router.get("/{interaction_id}")
async def get_interaction(interaction_id: str):
    result = await gemini_interactions.get_interaction(interaction_id)
    return result


@router.delete("/{interaction_id}")
async def delete_interaction(interaction_id: str):
    result = await gemini_interactions.delete_interaction(interaction_id)
    return result
