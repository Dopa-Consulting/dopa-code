"""AgentLoop — núcleo del agente Inti con tool-calling iterativo."""

import json
import asyncio
from pathlib import Path
from typing import Callable, Awaitable

from inti.openrouter_client import openrouter
from inti.config import settings
from inti.guardrails import guardrail_engine

SYSTEM_PROMPT = """Tu nombre es Inti. Eres el agente andino de Dopa Code, un entorno de desarrollo agentico Local-First.

Eres un agente que PUEDE ejecutar herramientas para cumplir las tareas que te pidan. Tienes DOS tipos de herramientas:

🔧 Herramientas locales (inspección y ediciones precisas):
- read_file, write_file, list_dir, run_command, git_diff
Úsalas para ediciones puntuales de 1-2 archivos, leer código, ejecutar comandos simples.

🤖 OpenCode (tareas grandes multi-archivo):
- run_opencode(task)
Úsala para construir features completas, scaffolding de proyectos, refactors amplios, o cualquier tarea que requiera editar múltiples archivos. OpenCode es un agente especializado que escribe y revisa código.

REGLAS:
1. Usa las herramientas disponibles para completar la tarea.
2. Para tareas grandes, delega a OpenCode con run_opencode.
3. Para ediciones precisas, usa las herramientas locales.
4. Observa el resultado de cada herramienta antes de decidir el siguiente paso.
5. Responde en texto SOLO cuando la tarea esté completa o si necesitas hacer una pregunta.
6. NO pidas confirmación para usar herramientas — simplemente úsalas.
7. Responde siempre en español neutro, en primera persona como Inti.
8. Sé directo y conciso.
9. Puedes usar recall_memory para consultar lecciones previas y skills del proyecto.
10. Algunos archivos están protegidos por guardrails. Si un write_file es bloqueado, NO insistas — explícale al usuario que ese archivo está protegido y por qué.
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
    {
        "type": "function",
        "function": {
            "name": "run_opencode",
            "description": (
                "Delega una tarea de código pesada o multi-archivo al agente OpenCode. "
                "Úsala para construir features/proyectos completos, NO para ediciones "
                "puntuales (para eso usa write_file/read_file)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Descripción de la tarea a delegar a OpenCode"}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": (
                "Recupera skills, lecciones previas y conocimiento del proyecto relevantes. "
                "Úsala antes de tareas grandes para no repetir errores."
            ),
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

# Tools que streamean su propio progreso (NO deben ser envueltas por el loop)
_STREAMING_TOOLS = {"run_opencode"}


class AgentLoop:
    def __init__(self, workspace: str, model: str | None = None, project_id: str | None = None, profile: str | None = None):
        self.workspace = Path(workspace).resolve()
        self.model = model or settings.architect_model
        self.project_id = project_id
        self.profile = profile
        self.max_iterations = 10

    def _resolve_path(self, path: str) -> Path:
        """Resuelve una ruta relativa al workspace y verifica que no escape.

        Usa is_relative_to (no startswith) para que un directorio hermano con
        prefijo común — p.ej. workspace `.../ws` y ruta `../ws-evil/x` — NO pase
        el check por coincidencia de string.
        """
        resolved = (self.workspace / path).resolve()
        if resolved != self.workspace and not resolved.is_relative_to(self.workspace):
            raise ValueError(f"Ruta fuera del workspace: {path}")
        return resolved

    def _check_guardrails(self, files_changed: list[str], diff_text: str) -> str | None:
        """Ejecuta el gate de guardrails. Devuelve None si pasa, o string de bloqueo."""
        if not self.profile:
            return None
        res = guardrail_engine.validate_diff(self.profile, diff_text, files_changed)
        if res.get("passed", True):
            return None
        msgs = "; ".join(v["message"] for v in res.get("violations", []))
        return f"BLOQUEADO por guardrails ({self.profile}): {msgs}"

    async def execute_tool(
        self,
        name: str,
        args: dict,
        emit: Callable[[dict], Awaitable[None]] | None = None,
    ) -> str:
        """Ejecuta una herramienta y devuelve el resultado como string.

        Si la herramienta streamea (ej. run_opencode), usa `emit` para enviar
        eventos step.start/step.delta/step.stop internamente.
        """
        try:
            if name == "read_file":
                path = self._resolve_path(args["path"])
                if not path.is_file():
                    return f"Error: el archivo no existe: {args['path']}"
                return path.read_text(encoding="utf-8")

            elif name == "write_file":
                path = self._resolve_path(args["path"])

                # Gate de guardrails ANTES de escribir
                block = self._check_guardrails([args["path"]], args["content"])
                if block:
                    return block

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

            elif name == "run_opencode":
                if emit is None:
                    return "Error: run_opencode requiere emit"
                return await self._run_opencode(args["task"], emit)

            elif name == "recall_memory":
                from inti.memory import MemoryContext
                return await MemoryContext.get_context_for_job(
                    self.project_id, self.profile or "general", limit=5)

            else:
                return f"Error: herramienta desconocida: {name}"

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error ejecutando {name}: {type(e).__name__}: {e}"

    async def _run_opencode(
        self,
        task: str,
        emit: Callable[[dict], Awaitable[None]],
    ) -> str:
        """Ejecuta OpenCode via bridge, streameando el progreso al Chat."""
        import httpx

        BRIDGE_URL = "http://localhost:4097"
        BRIDGE_TOKEN = "dopa-bridge-local-dev"

        collected: list[str] = []
        await emit({
            "event_type": "step.start",
            "data": {"tool": "run_opencode", "args": {"task": task}},
        })

        try:
            # dummy dentro del try para que el finally emita step.stop (framing
            # consistente en el Chat también en modo dummy).
            if settings.dopa_code_dummy:
                return "[DUMMY] OpenCode habría ejecutado: " + task[:200]
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{BRIDGE_URL}/run-stream",
                    headers={"x-bridge-token": BRIDGE_TOKEN},
                    json={
                        "prompt": task,
                        "directory": str(self.workspace),
                        "agent": "build",
                    },
                ) as resp:
                    if resp.status_code >= 400:
                        return f"OpenCode bridge error {resp.status_code}"

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            chunk = json.loads(line[6:])
                        except Exception:
                            continue
                        t = chunk.get("type")
                        if t in ("stdout", "stderr"):
                            txt = chunk.get("text", "")
                            collected.append(txt)
                            await emit({
                                "event_type": "step.delta",
                                "data": {"text": txt},
                            })
                        elif t == "exit":
                            collected.append(f"[exit {chunk.get('code')}]")
        except httpx.ConnectError:
            return (
                "El bridge de OpenCode no responde en :4097. "
                "Inícialo con bun bridge.js en agent-runtime/."
            )
        except httpx.TimeoutException:
            return "OpenCode excedió el tiempo límite (180s)."
        finally:
            await emit({
                "event_type": "step.stop",
                "data": {"index": 0},
            })

        # Obtener el diff resultante
        diff_text = ""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(
                    f"{BRIDGE_URL}/diff",
                    params={"directory": str(self.workspace)},
                    headers={"x-bridge-token": BRIDGE_TOKEN},
                )
                if r.status_code == 200:
                    data = r.json()
                    diff_text = data.get("diff_text", "")
        except Exception:
            pass

        summary = "OpenCode terminó.\n" + "\n".join(collected)[-2000:]
        if diff_text:
            summary += "\n\nDiff:\n" + diff_text[:3000]
        return summary

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

                is_streaming = name in _STREAMING_TOOLS

                if is_streaming:
                    # La tool maneja su propio framing (step.start/delta/stop)
                    result = await self.execute_tool(name, args, emit=emit)
                else:
                    # Tools locales: el loop emite el framing
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
