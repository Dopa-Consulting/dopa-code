"""AgentLoop — núcleo del agente Inti con tool-calling iterativo."""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Callable, Awaitable

from inti.openrouter_client import openrouter
from inti.config import settings

SYSTEM_PROMPT = """Tu nombre es Inti. Eres el agente andino de Dopa Code, un entorno de desarrollo agentico Local-First.

Eres un agente que PUEDE ejecutar herramientas para cumplir las tareas que te pidan. Tienes acceso a herramientas para leer archivos, escribir archivos, listar directorios, ejecutar comandos y ver diferencias de git.

REGLAS:
1. Usa las herramientas disponibles para completar la tarea.
2. Observa el resultado de cada herramienta antes de decidir el siguiente paso.
3. Responde en texto SOLO cuando la tarea esté completa o si necesitas hacer una pregunta.
4. NO pidas confirmación para usar herramientas — simplemente úsalas.
5. Responde siempre en español neutro, en primera persona como Inti.
6. Sé directo y conciso.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee el contenido de un archivo",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta relativa al archivo"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Escribe contenido en un archivo (lo crea si no existe, lo sobrescribe si existe)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta relativa al archivo"},
                    "content": {"type": "string", "description": "Contenido a escribir"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Lista el contenido de un directorio",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta relativa al directorio"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Ejecuta un comando en la terminal dentro del workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Comando a ejecutar"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Muestra los cambios actuales en el repositorio (git diff)",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
]


class AgentLoop:
    def __init__(self, workspace: str, model: str | None = None):
        self.workspace = Path(workspace).resolve()
        self.model = model or settings.architect_model
        self.max_iterations = 10

    def _resolve_path(self, path: str) -> Path:
        """Resuelve una ruta relativa al workspace y verifica que no escape."""
        resolved = (self.workspace / path).resolve()
        if not str(resolved).startswith(str(self.workspace)):
            raise ValueError(f"Ruta fuera del workspace: {path}")
        return resolved

    async def execute_tool(self, name: str, args: dict) -> str:
        """Ejecuta una herramienta y devuelve el resultado como string."""
        try:
            if name == "read_file":
                path = self._resolve_path(args["path"])
                if not path.is_file():
                    return f"Error: el archivo no existe: {args['path']}"
                return path.read_text(encoding="utf-8")

            elif name == "write_file":
                path = self._resolve_path(args["path"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(args["content"], encoding="utf-8")
                return f"Archivo escrito: {args['path']} ({len(args['content'])} caracteres)"

            elif name == "list_dir":
                path = self._resolve_path(args["path"])
                if not path.is_dir():
                    return f"Error: el directorio no existe: {args['path']}"
                items = sorted(p.name for p in path.iterdir())
                return "\n".join(items) if items else "(directorio vacío)"

            elif name == "run_command":
                proc = await asyncio.create_subprocess_shell(
                    args["command"],
                    cwd=str(self.workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=30.0
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return "Error: el comando excedió el tiempo límite (30s)"

                output = stdout.decode("utf-8", errors="replace")
                if stderr:
                    output += "\n[stderr]\n" + stderr.decode("utf-8", errors="replace")
                return output.strip() or "(sin salida)"

            elif name == "git_diff":
                proc = await asyncio.create_subprocess_shell(
                    "git diff",
                    cwd=str(self.workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=15.0
                )
                output = stdout.decode("utf-8", errors="replace")
                return output.strip() or "(sin cambios)"

            else:
                return f"Error: herramienta desconocida: {name}"

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error ejecutando {name}: {type(e).__name__}: {e}"

    async def run(
        self,
        user_message: str,
        emit: Callable[[dict], Awaitable[None]],
        history: list[dict] | None = None,
    ) -> None:
        """Ejecuta el loop observar→pensar→actuar hasta completar la tarea."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *(history or []),
            {"role": "user", "content": user_message},
        ]

        for _ in range(self.max_iterations):
            resp = await openrouter.chat(
                self.model, messages, tools=TOOL_SCHEMAS
            )

            if resp.get("error"):
                await emit({
                    "event_type": "error",
                    "payload": {"error": resp["error"]},
                })
                return

            tool_calls = resp.get("tool_calls")
            if not tool_calls:
                await emit({
                    "event_type": "chat_response",
                    "payload": {
                        "content": resp.get("content", ""),
                        "model": self.model,
                    },
                })
                return

            messages.append({
                "role": "assistant",
                "content": resp.get("content") or "",
                "tool_calls": tool_calls,
            })

            for i, tc in enumerate(tool_calls):
                fn = tc["function"]
                name = fn["name"]
                args = json.loads(fn["arguments"] or "{}")

                await emit({
                    "event_type": "step.start",
                    "data": {"tool": name, "args": args},
                })

                result = await self.execute_tool(name, args)

                await emit({
                    "event_type": "step.delta",
                    "data": {"text": f"🔧 {name} → {result[:800]}"},
                })

                await emit({
                    "event_type": "step.stop",
                    "data": {"index": i},
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        await emit({
            "event_type": "chat_response",
            "payload": {
                "content": "(alcancé el límite de iteraciones sin terminar)",
                "model": self.model,
            },
        })


# Instancia global
agent_loop = AgentLoop(workspace=str(Path.cwd()))
