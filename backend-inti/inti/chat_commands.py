"""Inti Chat Commands - Acceso directo a DB (sin HTTP loopback)."""

import json
import re
import subprocess
from pathlib import Path

from inti.config import settings
from inti.database import async_session
from inti.models.job import Job


async def execute_chat_command(workspace: str, message: str) -> dict:
    msg = message.strip()
    lower = msg.lower()

    # --- Crear sesion ---
    if "crea" in lower and "sesion" in lower:
        role = "builder" if ("builder" in lower or "build" in lower) else "architect"
        try:
            from inti.orchestrator import orchestrator
            session = orchestrator.create_session(role=role)
            return {"type": "action",
                    "content": f"**Sesion {role} creada**: `{session.id}`\nModelo: {session.model}"}
        except Exception as e:
            return {"type": "action", "content": f"Error: {e}"}

    # --- Crear Job real (cualquier tarea que empiece con verbo) ---
    verbs = ["crea", "hace", "haz", "genera", "construye", "diseña", "implementa",
             "desarrolla", "codifica", "modifica", "refactoriza", "corrige", "arregla",
             "añade", "agrega", "escribe"]
    first = lower.split(" ")[0] if " " in lower else lower
    if first in verbs and not any(w in lower for w in ["sesion", "carpeta", "directorio", "archivo", "folder"]):
        title = msg[:80] + ("..." if len(msg) > 80 else "")
        profile = "pro_mix"
        if any(w in lower for w in ["web", "landing", "pagina", "sitio", "frontend", "ui", "ux", "css", "html", "react", "design"]):
            profile = "dopaweb_theme"
        elif any(w in lower for w in ["api", "backend", "endpoint", "server"]):
            profile = "dopa_backend"
        elif any(w in lower for w in ["pago", "stripe", "mercadopago", "checkout"]):
            profile = "dopaweb_payment"

        try:
            async with async_session() as session:
                job = Job(title=title, description=msg, profile=profile,
                          autonomy_level="human_gatekeeper", status="planned")
                session.add(job)
                await session.commit()
                await session.refresh(job)

            from inti.audit import log_action
            await log_action(actor_type="human", action="created_job", job_id=job.id, summary=title)

            return {"type": "action",
                    "content": f"**Job `{job.id[:8]}` creado**\n{title}\nPerfil: {profile}\nEstado: planned"}
        except Exception as e:
            return {"type": "action", "content": f"Error: {str(e)[:200]}"}

    # --- Crear archivo ---
    if "archivo" in lower and any(w in lower for w in ["crea", "escribe"]):
        idx = lower.find("archivo")
        rest = msg[idx + 7:].strip().lstrip("con nombre ").strip("'\"")
        filename = rest.split("\n")[0].split(" en ")[0].strip() or "nuevo.md"
        filepath = Path(workspace) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(f"# {filename}\n\nCreado por Inti\n", encoding="utf-8")
        return {"type": "action", "content": f"**Archivo creado**: `{filepath}`"}

    # --- Crear carpeta ---
    if any(w in lower for w in ["carpeta", "directorio", "mkdir"]) and "crea" in lower:
        for kw in ["carpeta", "directorio", "mkdir"]:
            if kw in lower:
                idx = lower.find(kw)
                rest = msg[idx + len(kw):].strip().strip("'\"") or "nueva"
                dirpath = Path(workspace) / rest
                dirpath.mkdir(parents=True, exist_ok=True)
                return {"type": "action", "content": f"**Carpeta creada**: `{dirpath}`"}

    # --- Leer archivo ---
    if "lee" in lower and "archivo" in lower:
        idx = lower.find("archivo")
        rest = msg[idx + 7:].strip().strip("'\"")
        filename = rest.split("\n")[0].split(" ")[0].strip()
        if not filename:
            return {"type": "action", "content": "Cual archivo?"}
        filepath = Path(workspace) / filename
        if not filepath.exists():
            return {"type": "action", "content": f"**{filename}** no encontrado"}
        content = filepath.read_text(encoding="utf-8")
        ext = filename.split(".")[-1] if "." in filename else ""
        lang = {"py": "python", "js": "javascript", "ts": "typescript", "md": "markdown"}.get(ext, "")
        return {"type": "action", "content": f"**{filename}** ({len(content)} chars):\n```{lang}\n{content[:3000]}\n```"}

    # --- Listar archivos ---
    if "lista" in lower and "archivo" in lower or lower in ("ls", "dir"):
        files = sorted(Path(workspace).iterdir())[:30]
        lines = [f"**Workspace**: `{workspace}`\n"]
        for f in files:
            if not f.name.startswith("."):
                s = "/" if f.is_dir() else f" ({f.stat().st_size} bytes)"
                lines.append(f"- {f.name}{s}")
        return {"type": "action", "content": "\n".join(lines)}

    # --- Git ---
    if "diff" in lower or "cambio" in lower:
        r = subprocess.run(["git", "diff", "--stat"], cwd=workspace, capture_output=True, text=True, timeout=10)
        out = r.stdout.strip() or "No changes."
        return {"type": "action", "content": f"**Git diff**:\n```\n{out[:2000]}\n```"}

    if "status" in lower or "git" in lower:
        r = subprocess.run(["git", "status", "--short"], cwd=workspace, capture_output=True, text=True, timeout=10)
        out = r.stdout.strip() or "Clean."
        b = subprocess.run(["git", "branch", "--show-current"], cwd=workspace, capture_output=True, text=True, timeout=5)
        return {"type": "action", "content": f"**Git** (`{b.stdout.strip()}`):\n```\n{out[:2000]}\n```"}

    # --- Ayuda ---
    if any(w in lower for w in ["ayuda", "help", "que podes", "comandos"]):
        return {"type": "action", "content": (
            f"**Inti** - Workspace: `{workspace}`\n\n"
            "`crea landing page` → Job en pipeline FSM\n"
            "`crea un archivo X` → Archivo en workspace\n"
            "`crea una carpeta X` → Carpeta\n"
            "`lee el archivo X` → Leer\n"
            "`crea sesion builder` → Agente\n"
            "`lista archivos` `git diff` `git status`\n"
            "`/stream X` → Gemini streaming\n"
        )}

    # --- Comando no reconocido ---
    if any(first == w for w in verbs):
        return {"type": "action", "content": "No entiendo ese comando. Escribi `ayuda` para ver que puedo hacer."}

    # --- Conversacion → LLM ---
    try:
        from inti.memory import MemoryContext
        ctx = await MemoryContext.get_context_for_job(None, "pro_mix")
        if ctx and "[DUMMY]" not in ctx:
            return {"type": "chat", "content": f"{ctx}\n\n## Mensaje\n{message}"}
    except Exception:
        pass
    return {"type": "chat", "content": message}
