"""
Voice integration: ElevenLabs Speech Engine para Inti.

Flujo:
  PWA (microfono) → ElevenLabs STT (transcripcion)
                  → FastAPI Inti (/api/v1/voice/command)
                  → Procesa comando (FSM)
                  → ElevenLabs TTS (respuesta en voz)
                  → PWA (reproduce audio)

Comandos de voz soportados:
  "Inti, lista los ultimos 5 jobs"
  "Inti, ejecuta el job 42"
  "Inti, explica el job 10"
  "Inti, aprueba el job 7"
  "Inti, cual es el estado del deploy?"
"""

VOICE_COMMANDS = {
    "list_jobs": {
        "patterns": ["lista los jobs", "que jobs hay", "muestrame los jobs", "list jobs"],
        "handler": "list_recent_jobs",
    },
    "execute_job": {
        "patterns": ["ejecuta el job", "corre el job", "run job"],
        "handler": "execute_job_by_id",
    },
    "explain_job": {
        "patterns": ["explica el job", "que hizo el job", "explain job"],
        "handler": "explain_job",
    },
    "approve_job": {
        "patterns": ["aprueba el job", "aprove job", "mergea"],
        "handler": "approve_job",
    },
    "status": {
        "patterns": ["estado", "como va", "status", "que paso"],
        "handler": "system_status",
    },
}


def parse_voice_command(transcript: str) -> dict:
    """Parsea un comando de voz y devuelve el handler + parametros."""
    transcript_lower = transcript.lower()

    for cmd_name, cmd_info in VOICE_COMMANDS.items():
        for pattern in cmd_info["patterns"]:
            if pattern in transcript_lower:
                job_id = None
                import re
                match = re.search(r"job[:\s]*(\d+)", transcript_lower)
                if match:
                    job_id = match.group(1)
                return {
                    "command": cmd_name,
                    "handler": cmd_info["handler"],
                    "job_id": job_id,
                    "original": transcript,
                }

    return {
        "command": "unknown",
        "handler": None,
        "job_id": None,
        "original": transcript,
    }
