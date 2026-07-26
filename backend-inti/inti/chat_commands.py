# Comando de chat → accion real de Inti

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
    """
    Parsea un mensaje del Chat y ejecuta la accion correspondiente.
    Devuelve el resultado como dict con 'type' (action/chat) y 'content'.
    """
    msg_lower = message.lower().strip()

    # --- Crear sesion ---
    if "crea" in msg_lower and "sesion" in msg_lower:
        role = "builder" if "builder" in msg_lower or "build" in msg_lower else "architect"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8000/api/v1/sessions/",
                    json={"role": role},
                    timeout=5,
                )
                data = resp.json()
                return {
                    "type": "action",
                    "content": f"Sesion **{role}** creada: `{data.get('session_id', 'OK')}`\n\n"
                              f"Modelo: {data.get('model', 'default')}\n"
                              f"Estado: {data.get('status', 'active')}",
                }
        except Exception as e:
            return {"type": "action", "content": f"Error al crear sesion: {e}"}

    # --- Crear archivo ---
    create_match = re.search(r"crea(?:r)?\s+(?:un\s+)?archivo\s+(?:con\s+(?:nombre\s+)?)?[\"']?([^\"']+?)[\"']?\s*(?:en\s+)?(.+)?", msg_lower)
    if create_match or ("crea" in msg_lower and "archivo" in msg_lower):
        filename = (create_match.group(1) if create_match else "nuevo.md").strip()
        folder = (create_match.group(2) if create_match and create_match.group(2) else workspace).strip()
        filepath = Path(folder) / filename
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            content = f"# {filename}\n\nCreado por Inti - Dopa Code\n"
            filepath.write_text(content, encoding="utf-8")
            return {
                "type": "action",
                "content": f"Archivo **{filename}** creado en:\n`{filepath}`\n\n"
                          f"```\n{content}\n```"
            }
        except Exception as e:
            return {"type": "action", "content": f"Error al crear archivo: {e}"}

    # --- Leer archivo ---
    read_match = re.search(r"le(?:e|er)\s+(?:el\s+)?archivo\s+[\"']?([^\"']+)[\"']?", msg_lower)
    if read_match:
        filename = read_match.group(1).strip()
        filepath = Path(workspace) / filename
        try:
            content = filepath.read_text(encoding="utf-8")
            ext = filename.split(".")[-1] if "." in filename else ""
            lang = {"py": "python", "js": "javascript", "ts": "typescript", "tsx": "tsx", "md": "markdown"}.get(ext, "")
            return {
                "type": "action",
                "content": f"**{filename}** ({len(content)} caracteres):\n\n```{lang}\n{content[:3000]}\n```"
            }
        except FileNotFoundError:
            return {"type": "action", "content": f"Archivo **{filename}** no encontrado en el workspace."}
        except Exception as e:
            return {"type": "action", "content": f"Error al leer: {e}"}

    # --- Listar archivos ---
    if any(w in msg_lower for w in ["lista archivos", "que archivos hay", "ls", "dir"]):
        try:
            files = sorted(Path(workspace).rglob("*"))[:30]
            output = "**Archivos en el workspace:**\n\n"
            for f in files:
                if f.is_file() and not f.name.startswith(".") and "node_modules" not in str(f) and ".git" not in str(f):
                    rel = f.relative_to(workspace)
                    output += f"- `{rel}` ({f.stat().st_size} bytes)\n"
            return {"type": "action", "content": output}
        except Exception as e:
            return {"type": "action", "content": f"Error: {e}"}

    # --- Git diff ---
    if "diff" in msg_lower or "cambios" in msg_lower:
        try:
            result = subprocess.run(["git", "diff", "--stat"], cwd=workspace, capture_output=True, text=True, timeout=10)
            output = result.stdout.strip() or "No hay cambios."
            return {"type": "action", "content": f"**Git diff:**\n\n```\n{output[:2000]}\n```"}
        except Exception as e:
            return {"type": "action", "content": f"Error: {e}"}

    # --- Git status ---
    if "status" in msg_lower or "git" in msg_lower:
        try:
            result = subprocess.run(["git", "status", "--short"], cwd=workspace, capture_output=True, text=True, timeout=10)
            output = result.stdout.strip() or "Working tree limpio."
            return {"type": "action", "content": f"**Git status:**\n\n```\n{output[:2000]}\n```"}
        except Exception:
            pass

    # --- No es un comando → usar LLM ---
    return {"type": "chat", "content": message}
