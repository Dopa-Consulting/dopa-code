"""Inti Chat → Pipeline FSM real. Cada comando crea un Job que pasa por el pipeline completo."""

import asyncio
import json
import re
import subprocess
from pathlib import Path

import httpx

from inti.config import settings

BRIDGE_URL = "http://localhost:4097"
BRIDGE_TOKEN = "dopa-bridge-local-dev"


async def execute_chat_command(workspace: str, message: str) -> dict:
    msg = message.strip()
    lower = msg.lower()

    # --- Crear sesion (orchestrator real) ---
    if "crea" in lower and "sesion" in lower:
        role = "builder" if ("builder" in lower or "build" in lower) else "architect"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8000/api/v1/sessions/",
                    json={"role": role}, timeout=5,
                )
                data = resp.json()
                sid = data.get("session_id", "OK")
                return {"type": "action", "content": f"**Sesion {role} creada**: `{sid}`\nModelo: {data.get('model', 'default')}"}
        except Exception as e:
            return {"type": "action", "content": f"Error: {e}"}

    # --- Crear un Job real que pasa por el pipeline FSM ---
    if any(w in lower for w in ["crea un archivo", "crea archivo", "crea una carpeta", "crea carpeta",
                                 "escribe", "modifica", "refactoriza", "agrega", "implementa",
                                 "corrige", "arregla", "fixea", "optimiza", "mejora", "añade"]) \
       and not any(w in lower for w in ["sesion", "job"]):

        # Determinar el titulo del job
        title = msg[:80] + ("..." if len(msg) > 80 else "")
        profile = "dopaweb_theme" if any(w in lower for w in ["web", "pagina", "tienda", "ecommerce", "frontend", "ui", "ux", "css", "html"]) else "pro_mix"

        # Crear job via API
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8000/api/v1/jobs/",
                    json={
                        "title": title,
                        "description": msg,
                        "profile": profile,
                        "autonomy_level": "human_gatekeeper",
                    },
                    timeout=5,
                )
                if resp.status_code != 200:
                    return {"type": "action", "content": f"Error al crear job: {resp.text[:200]}"}

                data = resp.json()
                job_id = data.get("job_id", "?")

                # Iniciar el job (pipeline FSM)
                resp2 = await client.post(
                    f"http://localhost:8000/api/v1/jobs/{job_id}/start",
                    timeout=5,
                )
                start_data = resp2.json()

                context_lines = [
                    f"**Job creado e iniciado**: `{job_id[:8]}`",
                    f"Titulo: {title}",
                    f"Perfil: {profile}",
                    f"Estado: {start_data.get('status', 'executing')}",
                    f"Architect: {start_data.get('architect_model', '?')}",
                ]
                if start_data.get("plan"):
                    plan = start_data["plan"]
                    context_lines.append(f"\nPlan generado:\n```\n{str(plan)[:500]}\n```")

                return {"type": "action", "content": "\n".join(context_lines)}

        except Exception as e:
            # Fallback: si la API no responde, hacer file I/O directo
            return await _direct_file_action(workspace, msg, lower)

    # --- Comandos de consulta ---
    if "lee" in lower and "archivo" in lower:
        return await _read_file(workspace, msg, lower)
    if "lista" in lower and "archivo" in lower or lower in ("ls", "dir"):
        return await _list_files(workspace)
    if "diff" in lower or "cambio" in lower:
        return await _git_diff(workspace)
    if "status" in lower or "git" in lower:
        return await _git_status(workspace)
    if any(w in lower for w in ["ayuda", "help", "que podes hacer", "comandos"]):
        return await _help(workspace)

    # --- Comando no reconocido ---
    action_words = ["crea", "lee", "lista", "borra", "ejecuta", "deploy", "merge", "corre", "abre", "inicia"]
    if any(lower.startswith(w) or f" {w} " in f" {lower} " for w in action_words):
        return {"type": "action",
                "content": f"No reconozco ese comando.\n\n**Inti puede**: crear archivos, leer archivos, crear carpetas, crear sesiones de agente, ejecutar jobs con pipeline FSM, git diff, git status. Escribi `ayuda` para ver todos los comandos."}

    # --- Conversacion: LLM con contexto de memoria y skills ---
    enriched = await _enrich_with_context(msg)
    return {"type": "chat", "content": enriched}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _direct_file_action(workspace: str, msg: str, lower: str) -> dict:
    """Fallback: file I/O directo cuando la API no responde."""
    if "archivo" in lower:
        idx = lower.find("archivo")
        rest = msg[idx + 7:].strip().lstrip("con nombre ").strip("'\"")
        filename = rest.split("\n")[0].split(" en ")[0].strip() or "nuevo.md"
        filepath = Path(workspace) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = f"# {filename}\n\nCreado por Inti - Dopa Code\n"
        filepath.write_text(content, encoding="utf-8")
        return {"type": "action", "content": f"**Archivo creado** (modo directo): `{filepath}`"}
    if "carpeta" in lower or "directorio" in lower:
        idx = max(lower.find("carpeta") if "carpeta" in lower else -1,
                  lower.find("directorio") if "directorio" in lower else -1)
        rest = msg[idx:].split(" ", 1)[-1] if " " in msg[idx:] else ""
        dirname = rest.strip().strip("'\"") or "nueva"
        dirpath = Path(workspace) / dirname
        dirpath.mkdir(parents=True, exist_ok=True)
        return {"type": "action", "content": f"**Carpeta creada** (modo directo): `{dirpath}`"}
    return {"type": "action", "content": "No pude procesar esa accion."}


async def _read_file(workspace: str, msg: str, lower: str) -> dict:
    idx = lower.find("archivo")
    rest = msg[idx + 7:].strip().strip("'\"")
    filename = rest.split("\n")[0].split(" ")[0].strip()
    if not filename:
        return {"type": "action", "content": "Cual archivo?"}
    filepath = Path(workspace) / filename
    if not filepath.exists():
        return {"type": "action", "content": f"**{filename}** no encontrado en `{workspace}`"}
    content = filepath.read_text(encoding="utf-8")
    ext = filename.split(".")[-1] if "." in filename else ""
    lang_map = {"py": "python", "js": "javascript", "ts": "typescript", "tsx": "tsx", "md": "markdown", "json": "json"}
    lang = lang_map.get(ext, "")
    return {"type": "action", "content": f"**{filename}** ({len(content)} chars):\n\n```{lang}\n{content[:3000]}\n```"}


async def _list_files(workspace: str) -> dict:
    try:
        files = sorted(Path(workspace).iterdir())[:30]
        lines = [f"**Workspace**: `{workspace}`\n"]
        for f in files:
            if not f.name.startswith("."):
                suffix = "/" if f.is_dir() else f" ({f.stat().st_size} bytes)"
                lines.append(f"- {f.name}{suffix}")
        return {"type": "action", "content": "\n".join(lines)}
    except Exception as e:
        return {"type": "action", "content": f"Error: {e}"}


async def _git_diff(workspace: str) -> dict:
    try:
        result = subprocess.run(["git", "diff", "--stat"], cwd=workspace,
                                capture_output=True, text=True, timeout=10)
        out = result.stdout.strip() or "Working tree limpio."
        return {"type": "action", "content": f"**Git diff**:\n```\n{out[:2000]}\n```"}
    except Exception as e:
        return {"type": "action", "content": f"Error: {e}"}


async def _git_status(workspace: str) -> dict:
    try:
        result = subprocess.run(["git", "status", "--short"], cwd=workspace,
                                capture_output=True, text=True, timeout=10)
        out = result.stdout.strip() or "Limpio."
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=workspace,
                                capture_output=True, text=True, timeout=5)
        return {"type": "action", "content": f"**Git** (`{branch.stdout.strip()}`):\n```\n{out[:2000]}\n```"}
    except Exception:
        return {"type": "action", "content": "No es un repo git o error."}


async def _help(workspace: str) -> dict:
    return {"type": "action",
            "content": (
                f"**Inti** - Agente andino de Dopa Code\n"
                f"Workspace: `{workspace}`\n\n"
                "**Comandos** (crean Jobs reales con pipeline FSM):\n"
                "- `crea un archivo X` → Job → Planner → Executor → archivo\n"
                "- `crea una carpeta X` → carpeta en workspace\n"
                "- `lee el archivo X` → leer contenido\n"
                "- `lista archivos` → ver workspace\n"
                "- `crea sesion builder/architect` → sesion de agente\n"
                "- `git diff` / `git status`\n"
                "- `/stream X` → Gemini streaming\n"
                "- Preguntame cualquier cosa\n\n"
                "Cada job ejecutado aprende: PostMortem → lecciones → memoria."
            )}


async def _enrich_with_context(prompt: str) -> str:
    """Enriquece el prompt con contexto de memoria, skills y ERP si aplica."""
    try:
        from inti.memory import MemoryContext
        ctx = await MemoryContext.get_context_for_job(None, "pro_mix")
        if ctx and "[DUMMY]" not in ctx:
            return f"{ctx}\n\n## Mensaje\n{prompt}"
    except Exception:
        pass
    return prompt
