"""Inti Chat Commands - Parser simple para comandos reales."""

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

    # --- Crear sesion ---
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

    # --- Crear archivo ---
    if "crea" in lower and "archivo" in lower:
        # Extraer nombre: buscar palabra despues de "archivo"
        idx = lower.find("archivo")
        rest = msg[idx + 7:].strip().lstrip("con nombre ").strip("'\"")
        # Tomar la primera palabra o frase hasta salto de linea
        filename = rest.split("\n")[0].split(" en ")[0].strip()
        if not filename:
            filename = "nuevo.md"

        filepath = Path(workspace) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = f"# {filename}\n\nCreado por Inti - Dopa Code\n"
        filepath.write_text(content, encoding="utf-8")

        return {"type": "action",
                "content": f"**Archivo creado**: `{filepath}`\n\n```\n{content}\n```"}

    # --- Leer archivo ---
    if "lee" in lower and "archivo" in lower:
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
        return {"type": "action",
                "content": f"**{filename}** ({len(content)} chars):\n\n```{lang}\n{content[:3000]}\n```"}

    # --- Listar archivos ---
    if "lista" in lower and "archivo" in lower or lower in ("ls", "dir"):
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

    # --- Git diff ---
    if "diff" in lower or "cambio" in lower:
        try:
            result = subprocess.run(["git", "diff", "--stat"], cwd=workspace,
                                    capture_output=True, text=True, timeout=10)
            out = result.stdout.strip() or "Working tree limpio (no hay cambios)."
            return {"type": "action", "content": f"**Git diff**:\n```\n{out[:2000]}\n```"}
        except Exception as e:
            return {"type": "action", "content": f"Error: {e}"}

    # --- Git status ---
    if "status" in lower or "git" in lower:
        try:
            result = subprocess.run(["git", "status", "--short"], cwd=workspace,
                                    capture_output=True, text=True, timeout=10)
            out = result.stdout.strip() or "Limpio."
            branch = subprocess.run(["git", "branch", "--show-current"], cwd=workspace,
                                    capture_output=True, text=True, timeout=5)
            return {"type": "action",
                    "content": f"**Git** (branch: `{branch.stdout.strip()}`):\n```\n{out[:2000]}\n```"}
        except Exception:
            pass

    # --- Ayuda / que podes hacer ---
    if any(w in lower for w in ["ayuda", "help", "que podes hacer", "que eres capaz", "comandos"]):
        return {"type": "action",
                "content": (
                    "**Inti** - Agente andino de Dopa Code\n\n"
                    "**Workspace actual**: `{workspace}`\n\n"
                    "**Comandos**:\n"
                    "- `crea un archivo X` - Crea un archivo\n"
                    "- `lee el archivo X` - Lee un archivo\n"
                    "- `lista archivos` - Lista el workspace\n"
                    "- `crea sesion builder` - Nueva sesion de agente\n"
                    "- `git diff` - Ver cambios\n"
                    "- `git status` - Estado del repo\n"
                    "- `/stream X` - Streaming Gemini en vivo\n"
                ).format(workspace=workspace)}

    # --- No es comando → LLM ---
    return {"type": "chat", "content": message}
