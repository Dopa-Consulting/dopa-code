from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import Response

from inti.config import settings

router = APIRouter()


@router.post("/command")
async def voice_command(transcript: str = Form("")):
    from inti.voice import parse_voice_command, execute_voice_command
    parsed = parse_voice_command(transcript)
    result = await execute_voice_command(parsed)
    return {"parsed": parsed, "result": result}


@router.post("/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Transcribe audio via ElevenLabs STT. Devuelve texto."""
    if not settings.elevenlabs_api_key:
        return {"error": "ElevenLabs API key not configured", "transcript": ""}

    try:
        audio_bytes = await audio.read()
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": settings.elevenlabs_api_key},
                files={"audio": (audio.filename or "audio.webm", audio_bytes, audio.content_type or "audio/webm")},
                data={"model_id": "scribe_v1", "language_code": "es"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"transcript": data.get("text", ""), "confidence": data.get("confidence", 0)}
            return {"error": f"STT error {resp.status_code}", "transcript": ""}
    except Exception as e:
        return {"error": str(e), "transcript": ""}


@router.post("/speak")
async def voice_speak(text: str = Form("")):
    """Genera audio TTS via ElevenLabs. Devuelve audio/mpeg."""
    if not settings.elevenlabs_api_key or not text:
        return Response(content=b"", media_type="audio/mpeg")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
                headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_multilingual_v2"},
            )
            if resp.status_code == 200:
                return Response(content=resp.content, media_type="audio/mpeg")
            return Response(content=b"", media_type="audio/mpeg")
    except Exception:
        return Response(content=b"", media_type="audio/mpeg")
