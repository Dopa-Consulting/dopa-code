from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from inti.gemini_interactions import gemini_interactions, INTERACTIONS_MODELS

router = APIRouter()


@router.get("/models")
async def list_models():
    return {"models": [{"id": mid, **info} for mid, info in INTERACTIONS_MODELS.items()]}


@router.post("/chat")
async def chat(
    model: str = "gemini-2.5-flash",
    agent: str = "",
    user_input: str = "",
    system_instruction: str | None = None,
    background: bool = False,
):
    result = await gemini_interactions.interact(
        model=model,
        agent=agent,
        user_input=user_input,
        system_instruction=system_instruction,
        background=background,
    )
    return result


@router.post("/stream")
async def stream_chat(
    model: str = "gemini-2.5-flash",
    user_input: str = "",
):
    async def event_stream():
        async for chunk in gemini_interactions.interact_stream(model=model, user_input=user_input):
            import json as _json
            yield f"data: {_json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/deep-research")
async def deep_research(query: str):
    return await gemini_interactions.deep_research(query)


@router.post("/antigravity-qa")
async def antigravity_qa(code_or_diff: str, context: str = ""):
    return await gemini_interactions.antigravity_qa(code_or_diff, context)


@router.post("/continue")
async def continue_chat(user_input: str, previous_id: str = ""):
    return await gemini_interactions.continue_chat(user_input, previous_id)


@router.get("/{interaction_id}")
async def get_interaction(interaction_id: str):
    return await gemini_interactions.get_interaction(interaction_id)
