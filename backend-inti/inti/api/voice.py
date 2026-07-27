from fastapi import APIRouter, Body

from inti.voice import parse_voice_command

router = APIRouter()


@router.post("/command")
async def voice_command(transcript: str):
    parsed = parse_voice_command(transcript)
    return {
        "parsed": parsed,
        "response": f"Comando '{parsed['command']}' recibido.",
    }
