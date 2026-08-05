import logging
import re
from typing import Any

logger = logging.getLogger("inti.voice")

VOICE_COMMANDS: dict[str, dict] = {
    "list_jobs": {
        "patterns": ["lista los jobs", "que jobs hay", "muestrame los jobs", "list jobs", "pending tasks", "trabajos pendientes"],
        "handler": "list_recent_jobs",
        "description": "Lista los jobs recientes",
    },
    "execute_job": {
        "patterns": ["ejecuta el job", "corre el job", "run job", "execute job", "despliega job", "correr job"],
        "handler": "execute_job_by_id",
        "description": "Ejecuta un job especifico",
    },
    "explain_job": {
        "patterns": ["explica el job", "que hace el job", "explain job", "describe job", "dime del job"],
        "handler": "explain_job",
        "description": "Explica un job y su estado",
    },
    "approve_job": {
        "patterns": ["aprueba el job", "aprobar job", "approve job", "merge job", "acepta job"],
        "handler": "approve_job",
        "description": "Aprueba un job pendiente",
    },
    "status": {
        "patterns": ["estado del sistema", "system status", "como esta inti", "como estas", "que tal el sistema"],
        "handler": "system_status",
        "description": "Estado general del sistema",
    },
}


def parse_voice_command(transcript: str) -> dict[str, Any]:
    transcript_lower = transcript.lower().strip()

    for command_name, command_def in VOICE_COMMANDS.items():
        for pattern in command_def["patterns"]:
            if pattern in transcript_lower:
                job_id_match = re.search(r"job[:\s]*(\d+)", transcript_lower)
                return {
                    "command": command_name,
                    "handler": command_def["handler"],
                    "job_id": int(job_id_match.group(1)) if job_id_match else None,
                    "original": transcript,
                }

    return {"command": "unknown", "handler": None, "original": transcript}


async def execute_voice_command(parsed: dict) -> dict:
    """Ejecuta el handler real para un comando de voz parseado."""
    handler = parsed.get("handler")

    if handler == "list_recent_jobs":
        try:
            from inti.database import async_session
            from sqlalchemy import select
            from inti.models.job import Job
            async with async_session() as db:
                result = await db.execute(
                    select(Job).order_by(Job.updated_at.desc()).limit(5)
                )
                jobs = result.scalars().all()
                if not jobs:
                    return {"response": "No hay jobs recientes.", "action": "list_jobs", "count": 0}
                names = [f"Job {j.id[:8]}: {j.title[:60]} ({j.status})" for j in jobs]
                return {"response": "Jobs recientes: " + "; ".join(names), "action": "list_jobs", "count": len(jobs)}
        except Exception as e:
            return {"response": f"Error al listar jobs: {e}", "action": "list_jobs", "error": str(e)}

    elif handler == "execute_job_by_id" and parsed.get("job_id"):
        try:
            from inti.database import async_session
            from sqlalchemy import select
            from inti.models.job import Job
            async with async_session() as db:
                job = await db.get(Job, str(parsed["job_id"]))
                if not job:
                    return {"response": f"Job {parsed['job_id']} no encontrado.", "action": "execute"}
                return {"response": f"Iniciando ejecucion del job {job.id[:8]}: {job.title[:60]}", "action": "execute", "job_id": job.id}
        except Exception as e:
            return {"response": f"Error: {e}", "action": "execute", "error": str(e)}

    elif handler == "explain_job" and parsed.get("job_id"):
        try:
            from inti.database import async_session
            from inti.models.job import Job
            async with async_session() as db:
                job = await db.get(Job, str(parsed["job_id"]))
                if not job:
                    return {"response": f"Job {parsed['job_id']} no encontrado.", "action": "explain"}
                return {
                    "response": f"Job {job.id[:8]}: {job.title}. Estado: {job.status}. Perfil: {job.profile}.",
                    "action": "explain",
                    "job": {"id": job.id, "title": job.title, "status": job.status},
                }
        except Exception as e:
            return {"response": f"Error: {e}", "action": "explain", "error": str(e)}

    elif handler == "approve_job" and parsed.get("job_id"):
        return {"response": f"Para aprobar el job {parsed['job_id']}, usa el boton Approve en el dashboard.", "action": "approve", "job_id": parsed["job_id"]}

    elif handler == "system_status":
        from inti.orchestrator import orchestrator
        return {
            "response": f"Inti operativo. Sesiones activas: {orchestrator.active_count}/{orchestrator.total_sessions}.",
            "action": "status",
            "active_sessions": orchestrator.active_count,
            "total_sessions": orchestrator.total_sessions,
        }

    return {"response": f"Comando '{parsed.get('command', 'desconocido')}' recibido, pero no se como ejecutarlo.", "action": "unknown"}
