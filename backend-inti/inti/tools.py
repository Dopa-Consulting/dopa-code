"""Sistema de herramientas como plugins para Inti.

Cada tool es una clase con:
- schema: definicion JSON para OpenAI function calling
- execute(args): ejecuta la tool
- streaming: bool — si maneja su propio framing (step.start/delta/stop)

El ToolRegistry centraliza el catalogo y la ejecucion.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    required: list[str]
    execute_fn: Callable[..., Awaitable[str]]
    streaming: bool = False

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        return [t.schema for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    async def execute(self, name: str, args: dict,
                      emit: Callable[[dict], Awaitable[None]] | None = None) -> str:
        tool = self.get(name)
        if not tool:
            return f"Error: herramienta '{name}' no encontrada."
        if tool.streaming and emit:
            return await tool.execute_fn(args, emit=emit)
        return await tool.execute_fn(args)


# Registry global
registry = ToolRegistry()


# ── Herramientas built-in ──

async def _read_file(args: dict, workspace: Path, resolve_fn, guardrails_fn) -> str:
    path = resolve_fn(args["path"])
    if path.is_dir():
        items = sorted(p.name for p in path.iterdir())
        return f"'{args['path']}' es un directorio. Contenido:\n" + ("\n".join(items) if items else "(vacio)")
    if not path.is_file():
        if "schemas" in args["path"] or "tools/" in args["path"]:
            return "Error: no existe tools/schemas.py. Las tools estan en inti/agent_loop.py (registry)."
        return f"Error: el archivo no existe: {args['path']}"
    return path.read_text(encoding="utf-8")


async def _write_file(args: dict, workspace: Path, resolve_fn, guardrails_fn) -> str:
    path = resolve_fn(args["path"])
    block = guardrails_fn([args["path"]], args["content"])
    if block:
        return block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"Archivo escrito: {args['path']} ({len(args['content'])} caracteres)"


async def _list_dir(args: dict, workspace: Path, resolve_fn) -> str:
    path = resolve_fn(args["path"])
    if not path.is_dir():
        return f"Error: el directorio no existe: {args['path']}"
    items = sorted(p.name for p in path.iterdir())
    return "\n".join(items) if items else "(directorio vacío)"


async def _run_command(args: dict, workspace: Path) -> str:
    from inti.config import settings
    cmd = args["command"]
    # Validar whitelist
    cmd_parts = cmd.split()
    if cmd_parts:
        from inti.policies import is_command_allowed
        if not is_command_allowed(cmd_parts[0], cmd_parts[1:]):
            return f"BLOQUEADO por politicas: '{cmd_parts[0]}' no esta en la whitelist"
    timeout_s = getattr(settings, "run_command_timeout", 120)
    try:
        result = await asyncio.to_thread(
            subprocess.run, cmd, shell=True, cwd=str(workspace),
            capture_output=True, text=True, timeout=timeout_s,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        combined = out
        if err:
            combined += f"\n[stderr]\n{err}"
        return combined if combined else "(sin salida)"
    except subprocess.TimeoutExpired:
        return f"Timeout: el comando excedio {timeout_s}s"


async def _git_diff(args: dict, workspace: Path) -> str:
    import subprocess
    chk = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=str(workspace),
        capture_output=True, text=True,
    )
    if chk.returncode != 0:
        return "No es un repositorio git"
    result = subprocess.run(
        ["git", "diff"], cwd=str(workspace), capture_output=True, text=True,
    )
    return result.stdout.strip() or "(working tree limpio)"


async def _run_opencode(args: dict, workspace: Path) -> str:
    from inti.config import settings
    import httpx
    BRIDGE_URL = "http://localhost:4097"
    task = args.get("task", "")
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{BRIDGE_URL}/run-stream",
                headers={"x-bridge-token": settings.bridge_token or "dopa-bridge-local-dev"},
                json={"prompt": task, "directory": str(workspace), "agent": "build"},
            )
            if resp.status_code >= 400:
                return f"OpenCode bridge error {resp.status_code}"
            return resp.text[:5000] or "(sin respuesta del bridge)"
    except Exception as e:
        return f"Error bridge: {e}"


async def _web_fetch(args: dict) -> str:
    import re
    import httpx
    url = args.get("url", "")
    if not url.startswith(("http://", "https://")):
        return "URL invalida"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, follow_redirects=True)
            body = resp.text
            html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body)
            text = re.sub(r"(?s)<[^>]+>", " ", html)
            text = re.sub(r"&nbsp;", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:8000] if text else f"(sin contenido de texto en {url})"
    except Exception as e:
        return f"Error fetching {url}: {e}"


async def _save_memory(args: dict) -> str:
    from inti.database import async_session
    from inti.models.project_knowledge import ProjectKnowledge
    try:
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(ProjectKnowledge).where(ProjectKnowledge.key == args["key"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = args["value"]
            else:
                db.add(ProjectKnowledge(key=args["key"], value=args["value"]))
            await db.commit()
        return f"Memoria guardada: {args['key']}"
    except Exception as e:
        return f"Error guardando memoria: {e}"


async def _recall_memory(args: dict) -> str:
    from inti.database import async_session
    from inti.models.project_knowledge import ProjectKnowledge
    try:
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(ProjectKnowledge).where(ProjectKnowledge.key == args.get("key", ""))
            )
            entry = result.scalar_one_or_none()
            if entry:
                return entry.value or "(vacio)"
            return f"No hay memoria para '{args.get('key', '')}'"
    except Exception as e:
        return f"Error recuperando memoria: {e}"


async def _generate_image(args: dict) -> str:
    from inti.config import settings
    prompt = args.get("prompt", "")
    if not settings.google_api_key:
        return "Google API key no configurada"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-exp:generateContent?key={settings.google_api_key}",
                json={
                    "contents": [{"parts": [{"text": f"Generate image: {prompt}"}]}],
                    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
                },
            )
            if resp.status_code == 200:
                return f"Imagen generada para prompt: {prompt[:100]}"
            return f"Error API imagen: {resp.status_code}"
    except Exception as e:
        return f"Error generando imagen: {e}"


# ── Registro de herramientas ──

def register_builtin_tools(workspace: Path, resolve_fn, guardrails_fn):
    registry.register(Tool("read_file", "Lee el contenido de un archivo",
        {"path": {"type": "string", "description": "Ruta relativa al archivo"}},
        ["path"],
        lambda args: _read_file(args, workspace, resolve_fn, guardrails_fn)))

    registry.register(Tool("write_file", "Escribe contenido en un archivo",
        {"path": {"type": "string", "description": "Ruta relativa"}, "content": {"type": "string", "description": "Contenido"}},
        ["path", "content"],
        lambda args: _write_file(args, workspace, resolve_fn, guardrails_fn)))

    registry.register(Tool("list_dir", "Lista el contenido de un directorio",
        {"path": {"type": "string", "description": "Ruta relativa al directorio"}},
        ["path"],
        lambda args: _list_dir(args, workspace, resolve_fn)))

    registry.register(Tool("run_command", "Ejecuta un comando en la terminal",
        {"command": {"type": "string", "description": "Comando a ejecutar"}},
        ["command"],
        lambda args: _run_command(args, workspace)))

    registry.register(Tool("git_diff", "Muestra cambios actuales en git",
        {}, [],
        lambda args: _git_diff(args, workspace)))

    registry.register(Tool("run_opencode", "Delega tarea multi-archivo a OpenCode",
        {"task": {"type": "string", "description": "Descripcion de la tarea"}},
        ["task"],
        lambda args: _run_opencode(args, workspace),
        streaming=True))

    registry.register(Tool("web_fetch", "Lee el contenido de una pagina web",
        {"url": {"type": "string", "description": "URL a leer"}},
        ["url"],
        _web_fetch))

    registry.register(Tool("save_memory", "Guarda informacion en la memoria del proyecto",
        {"key": {"type": "string", "description": "Clave"}, "value": {"type": "string", "description": "Valor"}},
        ["key", "value"],
        _save_memory))

    registry.register(Tool("recall_memory", "Recupera informacion de la memoria",
        {"key": {"type": "string", "description": "Clave a buscar"}},
        ["key"],
        _recall_memory))

    registry.register(Tool("generate_image", "Genera una imagen con IA",
        {"prompt": {"type": "string", "description": "Descripcion de la imagen"}},
        ["prompt"],
        _generate_image,
        streaming=True))
