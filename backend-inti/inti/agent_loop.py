"""AgentLoop — núcleo del agente Inti con tool-calling iterativo."""

import json
import asyncio
from pathlib import Path
from typing import Callable, Awaitable

from inti.openrouter_client import openrouter
from inti.config import settings
from inti.guardrails import guardrail_engine

SYSTEM_PROMPT = """Tu nombre es Inti. Eres el agente andino de Dopa Code, un entorno de desarrollo agentico Local-First.

Eres un agente que DEBE ejecutar herramientas para cumplir las tareas. NO eres un chatbot. CADA mensaje del usuario que empiece con un verbo de accion (crea, construye, genera, escribe, modifica, etc.) DEBE resultar en una llamada a herramienta. JAMAS respondas solo con texto a un comando de accion.

Tienes estas herramientas:
- read_file, write_file, list_dir, run_command, git_diff → ediciones precisas
- run_opencode(task) → tareas grandes multi-archivo
- recall_memory → consultar skills y lecciones previas

REGLAS:
1. SIEMPRE usa herramientas para comandos de accion. NUNCA respondas solo con texto.
2. Para tareas grandes: run_opencode. Para ediciones puntuales: write_file.
3. Observa el resultado antes del siguiente paso.
4. Solo responde con texto cuando la tarea este COMPLETA.
5. NO pidas confirmacion — USA las herramientas directamente.
6. Responde en español, en primera persona como Inti.
7. Si no sabes que hacer, usa recall_memory o preguntame.
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
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": (
                "Genera una imagen usando IA (Nano Banana de Gemini). "
                "Guarda el PNG en el workspace. Ideal para landing pages, banners, "
                "portadas de README, o cualquier recurso visual."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Descripcion de la imagen a generar"},
                    "filename": {"type": "string", "description": "Nombre del archivo PNG (ej: portada.png)"},
                },
                "required": ["prompt", "filename"]
            }
        }
    },
]

# Tools que streamean su propio progreso (NO deben ser envueltas por el loop)
_STREAMING_TOOLS = {"run_opencode"}


class AgentLoop:
    def __init__(self, workspace: str, model: str | None = None, project_id: str | None = None, profile: str | None = None, require_approval: bool = False):
        self.workspace = Path(workspace).resolve()
        self.model = model or settings.architect_model
        self.project_id = project_id
        self.profile = profile
        self.require_approval = require_approval
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

            elif name == "generate_image":
                return await self._generate_image(args, emit)

            else:
                return f"Error: herramienta desconocida: {name}"

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error ejecutando {name}: {type(e).__name__}: {e}"

    async def _generate_image(self, args: dict, emit: Callable[[dict], Awaitable[None]] | None) -> str:
        """Genera imagen con Nano Banana (Gemini) y la guarda en el workspace."""
        from inti.gemini_interactions import gemini_interactions

        if not gemini_interactions.is_configured:
            return "Error: Gemini API key no configurada. Agregala en Modelos > Google AI."

        prompt = args.get("prompt", "")[:500]
        filename = args.get("filename", "generated.png")

        if len(args.get("prompt", "")) > 500:
            prompt += " (truncado a 500 chars)"

        await emit({"event_type": "step.start", "data": {"tool": "generate_image", "args": {"prompt": prompt[:100]}}}) if emit else None

        result = await gemini_interactions.interact(
            model="gemini-2.5-flash-image",
            user_input=f"Generate ONLY an image: {prompt}. Do not respond with text, only generate the image.",
        )

        if "error" in result or not any(
            block.get("type") == "image"
            for step in result.get("steps", [])
            for block in step.get("content", [])
        ):
            # Retry con Nano Banana 2 Lite
            result = await gemini_interactions.interact(
                model="gemini-3.1-flash-lite-image",
                user_input=f"Generate an image of: {prompt}",
            )

        # Extraer imagen base64 de la respuesta
        import base64
        image_data = ""
        for step in result.get("steps", []):
            if step.get("type") == "model_output":
                for block in step.get("content", []):
                    if block.get("type") == "image" and block.get("data"):
                        image_data = block["data"]
                        break

        if not image_data:
            return f"El modelo no genero imagen. Respuesta: {result.get('output', '')[:500]}"

        filepath = self.workspace / filename
        filepath.write_bytes(base64.b64decode(image_data))

        if emit:
            await emit({"event_type": "step.delta", "data": {"text": f"Imagen guardada: {filename}"}})
            await emit({"event_type": "step.stop", "data": {"index": 0}})

        return f"Imagen generada y guardada como {filename} ({filepath.stat().st_size} bytes) en {self.workspace}"

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
        # Auto-inyección de memoria RELEVANTE en el system prompt (Prioridad 1).
        # La tool recall_memory sigue disponible para búsquedas profundas, pero el
        # LLM casi nunca la pide solo; el contexto relevante va SIEMPRE presente.
        system_content = SYSTEM_PROMPT
        try:
            from inti.memory import MemoryContext
            mem = await MemoryContext.get_context_for_job(
                self.project_id, self.profile or "general", limit=5
            )
            if mem and "- " in mem and "[DUMMY]" not in mem:
                system_content = SYSTEM_PROMPT + "\n\n" + mem
        except Exception:
            pass

        messages = [
            {"role": "system", "content": system_content},
            *(history or []),
            {"role": "user", "content": user_message},
        ]

        for _ in range(self.max_iterations):
            resp = await openrouter.chat(
                self.model, messages, tools=TOOL_SCHEMAS
            )

            # Si OpenRouter falla (sin creditos, billing), intentar con Gemini
            if resp.get("error"):
                from inti.gemini_interactions import gemini_interactions as gi

                if gi.is_configured and ("402" in str(resp.get("detail", "")) or "credit" in str(resp.get("error", "")).lower() or "billing" in str(resp.get("error", "")).lower()):
                    # OpenRouter sin creditos → Gemini como fallback
                    gemini_result = await gi.interact(
                        model="gemini-2.5-flash",
                        user_input=user_message,
                    )
                    if "error" not in gemini_result:
                        await emit({
                            "event_type": "chat_response",
                            "payload": {
                                "content": gemini_result.get("output", ""),
                                "model": "gemini (openrouter sin creditos)",
                            },
                        })
                        return

                await emit({
                    "event_type": "error",
                    "payload": {"error": resp["error"]},
                })
                return

            tool_calls = resp.get("tool_calls")
            if not tool_calls:
                # LLM terminó. Si require_approval, crear checkpoint.
                if self.require_approval:
                    job_id = await self._create_checkpoint(user_message, emit)
                    if job_id:
                        await emit({
                            "event_type": "chat_response",
                            "payload": {
                                "content": (
                                    f"Propuse cambios (job {job_id[:8]}). "
                                    "Revisa el diff y aprueba o rechaza."
                                ),
                                "model": self.model,
                                "job_id": job_id,
                            },
                        })
                        return
                    # Sin cambios en git → igual crear job simple con la respuesta
                    job_id = await self._create_simple_checkpoint(user_message, resp.get("content", ""), emit)
                    if job_id:
                        await emit({
                            "event_type": "chat_response",
                            "payload": {
                                "content": (
                                    f"{resp.get('content', '')}\n\n"
                                    f"(Job {job_id[:8]} creado sin cambios de codigo)"
                                ),
                                "model": self.model,
                                "job_id": job_id,
                            },
                        })
                        return
                # Sin checkpoint → chat_response normal
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

    async def _create_simple_checkpoint(self, user_message: str, response: str, emit: Callable[[dict], Awaitable[None]]) -> str | None:
        """Crea un Job simple sin diff (cuando no hubo cambios en el working tree)."""
        from inti.database import async_session
        from inti.models.job import Job
        from inti.events import job_state_changed

        async with async_session() as session:
            job = Job(
                title=user_message[:120],
                description=f"{user_message}\n\nRespuesta del agente:\n{response}",
                profile=self.profile or "pro_mix",
                repo_id=str(self.workspace),
                status="awaiting_approval",
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        await emit(job_state_changed(job_id, "running", "awaiting_approval").to_dict())
        return job_id

    async def _create_checkpoint(self, user_message: str, emit: Callable[[dict], Awaitable[None]]) -> str | None:
        """Captura diff del working tree, crea Job+Diff en DB, emite DiffReadyForApproval."""
        import subprocess

        from inti.database import async_session
        from inti.models.job import Job
        from inti.models.diff import Diff
        from inti.events import diff_ready, job_state_changed

        ws = str(self.workspace)

        # ¿Es repo git?
        chk = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ws, capture_output=True, text=True,
        )
        if chk.returncode != 0:
            return None  # no es git → sin checkpoint

        # Capturar diff de todo el working tree (incluye archivos nuevos)
        subprocess.run(["git", "add", "-A"], cwd=ws, capture_output=True, text=True)
        diff = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=ws, capture_output=True, text=True,
        ).stdout
        if not diff.strip():
            return None  # nada que aprobar

        names_out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=ws, capture_output=True, text=True,
        ).stdout.strip()
        names = names_out.split("\n") if names_out else []

        async with async_session() as session:
            job = Job(
                title=user_message[:120],
                description=user_message,
                profile=self.profile or "pro_mix",
                repo_id=ws,
                status="awaiting_approval",
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

            diff_rec = Diff(
                job_id=job.id,
                summary=user_message[:200],
                diff_text=diff[:50000],
                files_changed=str(names),
                status="pending",
            )
            session.add(diff_rec)
            await session.commit()
            await session.refresh(diff_rec)
            job_id, diff_id = job.id, diff_rec.id

        await emit(job_state_changed(job_id, "running", "awaiting_approval").to_dict())
        await emit(diff_ready(job_id, diff_id, user_message[:200], len(names)).to_dict())
        return job_id


# Instancia global
agent_loop = AgentLoop(workspace=str(Path.cwd()))
