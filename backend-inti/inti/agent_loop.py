"""AgentLoop — núcleo del agente Inti con tool-calling iterativo."""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Callable, Awaitable

from inti.openrouter_client import openrouter
from inti.config import settings
from inti.guardrails import guardrail_engine

SYSTEM_PROMPT = """Tu nombre es Inti. Eres el agente de código de Dopa Code, un entorno de desarrollo agéntico Local-First. Ejecutas, no describes intenciones: haces. Español neutro LATAM (tú, nunca vos), primera persona como Inti.

## Cómo trabajas (lo más importante)
Eres un agente de tool-calling: observas → actúas → observas, hasta terminar.
- PREGUNTAS CONVERSACIONALES: Si el usuario hace una pregunta simple (Hola, cómo estás, qué modelo usas, qué puedes hacer, cuál es tu nombre…) responde DIRECTAMENTE en texto. NO uses herramientas para preguntas conversacionales.
- Ante un COMANDO de ACCIÓN (crea, escribe, modifica, arregla, analiza, diagnostica, revisa…) SIEMPRE usas herramientas. Jamás respondas solo con texto a un comando de acción.
- Para ANALIZAR o DIAGNOSTICAR: LEE los archivos relevantes con read_file (usa list_dir para orientarte), razona sobre su contenido, y ENTREGA un análisis concreto en texto. No te quedes explorando; tras reunir contexto suficiente SIEMPRE das tu conclusión.
- Sé eficiente: lee los archivos que importan, no explores sin rumbo.
- CIERRA el loop: cuando termines, responde en TEXTO con el resultado o el análisis. NUNCA termines sin respuesta ni con contenido vacío.
- No pidas confirmación — usa las herramientas directamente.

## Tus herramientas
- read_file, write_file, list_dir, git_diff — leer/editar código y ver cambios
- run_command — comandos de shell del sistema
- run_opencode(task) — delegar tareas grandes multi-archivo
- recall_memory — skills y lecciones previas · web_fetch — leer webs · generate_image — imágenes

## Entorno (IMPORTANTE — NO es WSL)
Corres en el host de Dopa Code (Windows en local, Linux en Contabo). run_command usa el shell del sistema, que NO siempre tiene comandos Unix. Para inspeccionar archivos PREFIERE read_file/list_dir en vez de shell (grep, cat, sed, ls pueden no existir o diferir según el SO). Si usas shell, comandos simples; verifica el SO si dudas.

## Contexto Dopa
Ecosistema de José Castañeda: DopaCRM (ERP/POS/facturación SUNAT, Node+React), Dopa Commerce (storefront Payload+Next), Dopa Code (tú). Claude = arquitecto/auditor; Hermes = ejecución; tú = agente de código Dopa-nativo con memoria + skills de dominio.

## Tu modelo
Corres con **{model}** como tu LLM. Eres rápido, barato y nativo de Dopa Code. No inventes qué modelo usas — si te preguntan, di el nombre exacto que ves aquí: {model}.

## Diseño (si generas UI)
Clean Solid dark (bg #0B0E11, texto #E2E8F0), gradiente 90° #00E9D9 → #6900FF (texto blanco sobre gradiente), tipografía Geist. Sin glassmorphism, sin emojis, sin colores hardcodeados (CSS vars). NUNCA uses sed en TSX — reescribe con write_file.
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
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Descarga una URL de internet y devuelve su contenido en texto "
                "(HTML convertido a texto plano; JSON/texto tal cual). Úsala para "
                "leer documentación viva, validar catálogos de APIs (p.ej. los "
                "modelos de OpenRouter en https://openrouter.ai/api/v1/models), o "
                "consultar cualquier recurso web."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa (https://...) a descargar"},
                },
                "required": ["url"]
            }
        }
    },
]

# Tools que streamean su propio progreso (NO deben ser envueltas por el loop)
_STREAMING_TOOLS = {"run_opencode", "generate_image"}


class AgentLoop:
    def __init__(self, workspace: str, model: str | None = None, project_id: str | None = None, profile: str | None = None, require_approval: bool = False, allowed_dirs: list[str] | None = None, use_heavy_model: bool = False):
        self.workspace = Path(workspace).resolve()
        self.model = model or (settings.heavy_model if use_heavy_model else settings.loop_model)
        self.heavy_model = settings.heavy_model
        self.use_heavy_model = use_heavy_model
        self.project_id = project_id
        self.profile = profile
        self.require_approval = require_approval
        self.max_iterations = settings.max_iterations
        self.allowed_dirs = [Path(d).resolve() for d in (allowed_dirs or []) if Path(d).is_dir()]

    def _resolve_path(self, path: str) -> Path:
        """Resuelve una ruta relativa al workspace. Permite allowed_dirs."""
        resolved = (self.workspace / path).resolve()
        if resolved != self.workspace and not resolved.is_relative_to(self.workspace):
            for ad in self.allowed_dirs:
                if resolved == ad or resolved.is_relative_to(ad):
                    return resolved
            raise ValueError(f"Ruta fuera del workspace: {path}")
        return resolved

    async def _chat(self, messages: list[dict], tools: list[dict]) -> dict:
        """Routea la llamada LLM: DeepSeek directo (barato) o OpenRouter."""
        if "deepseek" in self.model and "deepseek/deepseek" not in self.model:
            from inti.config import settings
            from inti.openrouter_client import multiprovider
            key = multiprovider.providers.get("deepseek") or settings.deepseek_api_key
            if key:
                resp = await multiprovider.chat("deepseek", self.model, messages, 8000, tools=(tools if tools else None))
                if "error" not in resp and resp.get("content"):
                    return resp
                # Si DeepSeek devuelve vacio con tools, reintentar sin tools
                if "error" not in resp:
                    resp2 = await multiprovider.chat("deepseek", self.model, messages, 8000)
                    if "error" not in resp2 and resp2.get("content"):
                        return resp2
        # Fallback a OpenRouter
        return await openrouter.chat(self.model, messages, tools=tools)
        """Resuelve una ruta relativa al workspace y verifica que no escape.

        Usa is_relative_to (no startswith) para que un directorio hermano con
        prefijo común — p.ej. workspace `.../ws` y ruta `../ws-evil/x` — NO pase
        el check por coincidencia de string.
        """
        resolved = (self.workspace / path).resolve()
        if resolved != self.workspace and not resolved.is_relative_to(self.workspace):
            for ad in self.allowed_dirs:
                if resolved == ad or resolved.is_relative_to(ad):
                    return resolved
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
                    if "schemas" in args["path"] or "tools/" in args["path"]:
                        return "Error: no existe tools/schemas.py. Las tools estan en inti/agent_loop.py (TOOL_SCHEMAS). Usa read_file con path=ini/agent_loop.py."
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
                # subprocess.run en un thread. asyncio.create_subprocess_shell lanza
                # NotImplementedError en Windows bajo el SelectorEventLoop (uvicorn) →
                # dejaba a Inti sin terminal. to_thread evita la maquinaria de
                # subprocess del event loop y funciona en cualquier plataforma.
                timeout_s = getattr(settings, "run_command_timeout", 120)
                try:
                    result = await asyncio.to_thread(
                        subprocess.run,
                        args["command"],
                        shell=True,
                        cwd=str(self.workspace),
                        capture_output=True,
                        text=True,
                        timeout=timeout_s,
                    )
                except subprocess.TimeoutExpired:
                    return f"Error: el comando excedió el tiempo límite ({timeout_s}s)"
                output = result.stdout or ""
                if result.stderr:
                    output += "\n[stderr]\n" + result.stderr
                return output.strip() or "(sin salida)"

            elif name == "git_diff":
                try:
                    result = await asyncio.to_thread(
                        subprocess.run,
                        ["git", "diff"],
                        cwd=str(self.workspace),
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                except subprocess.TimeoutExpired:
                    return "Error: git diff excedió el tiempo límite (15s)"
                return (result.stdout or "").strip() or "(sin cambios)"

            elif name == "run_opencode":
                if emit is None:
                    return "Error: run_opencode requiere emit"
                return await self._run_opencode(args["task"], emit)

            elif name == "recall_memory":
                from inti.memory import MemoryContext
                return await MemoryContext.get_context_for_job(
                    self.project_id, self.profile or "general", limit=5)

            elif name == "save_memory":
                return await self._save_memory(args)

            elif name == "generate_image":
                return await self._generate_image(args, emit)

            elif name == "web_fetch":
                return await self._web_fetch(args)

            else:
                return f"Error: herramienta desconocida: {name}"

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error ejecutando {name}: {type(e).__name__}: {e}"

    async def _save_memory(self, args: dict) -> str:
        """Guarda informacion en ProjectKnowledge (persistente entre sesiones)."""
        from inti.database import async_session
        from inti.models.project_knowledge import ProjectKnowledge
        from sqlalchemy import select

        key = args.get("key", "")
        value = args.get("value", "")
        if not key or not value:
            return "Error: key y value requeridos"

        pid = self.project_id or "general"
        async with async_session() as session:
            result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == pid,
                    ProjectKnowledge.key == key,
                )
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.value = value
            else:
                entry = ProjectKnowledge(project_id=pid, key=key, value=value)
                session.add(entry)
            await session.commit()

        return f"Guardado: {key} = {value[:500]} (proyecto: {pid})"

    async def _generate_image(self, args: dict, emit: Callable[[dict], Awaitable[None]] | None) -> str:
        """Genera una imagen con Gemini (Nano Banana) vía el endpoint generateContent
        y la guarda en el workspace.

        NO usa la Interactions API (interact()): esa es un flujo de texto/agente y
        NUNCA devuelve bloques de imagen — por eso la versión previa se colgaba y
        nunca producía nada. Acá se llama al modelo de imagen directo con
        responseModalities=IMAGE y se extrae el base64 de inlineData.
        """
        import base64
        import httpx

        prompt = (args.get("prompt") or "").strip()
        if not prompt:
            return "Error: falta 'prompt' para generar la imagen."

        filename = args.get("filename") or "generated.png"
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            filename += ".png"

        key = settings.google_api_key
        if not key or key.endswith("...") or not key.startswith(("AQ.", "AIza")):
            return "Error: Google API key inválida o ausente. Configúrala en Modelos > Google AI."

        if settings.dopa_code_dummy:
            return f"[DUMMY] Habría generado una imagen para: {prompt[:80]}"

        try:
            path = self._resolve_path(filename)
        except ValueError as e:
            return f"Error: {e}"

        if emit:
            await emit({"event_type": "step.start", "data": {"tool": "generate_image", "args": {"prompt": prompt[:100]}}})

        model = "gemini-2.5-flash-image"
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"responseModalities": ["IMAGE"]},
                    },
                )
        except httpx.TimeoutException:
            if emit:
                await emit({"event_type": "step.stop", "data": {"index": 0}})
            return "Error: la generación de imagen excedió el tiempo límite (90s)."
        except Exception as e:
            if emit:
                await emit({"event_type": "step.stop", "data": {"index": 0}})
            return f"Error llamando a Gemini image: {type(e).__name__}: {e}"

        if resp.status_code != 200:
            if emit:
                await emit({"event_type": "step.stop", "data": {"index": 0}})
            return f"Error de Gemini image ({resp.status_code}): {resp.text[:300]}"

        # Extraer el base64 real de inlineData (soporta inlineData e inline_data).
        b64 = ""
        for c in resp.json().get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                inline = p.get("inlineData") or p.get("inline_data")
                if inline and inline.get("data"):
                    b64 = inline["data"]
                    break
            if b64:
                break

        if not b64:
            if emit:
                await emit({"event_type": "step.stop", "data": {"index": 0}})
            return "El modelo no devolvió una imagen. Probá reformular el prompt."

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(b64))

        if emit:
            await emit({"event_type": "step.delta", "data": {"text": f"🖼️ Imagen guardada: {filename}"}})
            await emit({"event_type": "step.stop", "data": {"index": 0}})

        return f"Imagen generada y guardada en {filename} ({path.stat().st_size} bytes)."

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

    async def _web_fetch(self, args: dict) -> str:
        """Descarga una URL y devuelve su contenido en texto (HTML → texto plano)."""
        import re
        import httpx

        url = (args.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            return "Error: URL inválida (debe empezar con http:// o https://)."

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "DopaCode-Inti/1.0"})
        except httpx.TimeoutException:
            return "Error: la descarga excedió el tiempo límite (30s)."
        except Exception as e:
            return f"Error descargando {url}: {type(e).__name__}: {e}"

        if resp.status_code >= 400:
            return f"Error HTTP {resp.status_code} al descargar {url}."

        ctype = resp.headers.get("content-type", "")
        body = resp.text

        # JSON o texto plano: tal cual (truncado).
        if "json" in ctype or "text/plain" in ctype:
            return body[:8000]

        # HTML → texto plano básico (quita script/style + tags).
        html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body)
        text = re.sub(r"(?s)<[^>]+>", " ", html)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000] if text else f"(sin contenido de texto en {url})"

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
        system_content = SYSTEM_PROMPT.replace("{model}", self.model)
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

        previous_tool_calls: set[str] = set()  # Guard contra repeticion

        for iteration in range(self.max_iterations):
            # Routing: DeepSeek directo (sin OpenRouter markup) o OpenRouter
            resp = await self._chat(messages, TOOL_SCHEMAS)

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
                # LLM terminó.
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
                content = resp.get("content", "") or ""
                # Si el contenido es puro JSON (el LLM intento tool-calling por texto), limpiarlo
                if content.strip().startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                    if len(content) < 20:
                        content = "Procesando tu solicitud. Intentemos algo mas especifico."
                # El modelo terminó con contenido VACÍO (deepseek suele hacerlo tras
                # explorar): si ya investigó, forzar la síntesis en vez de "Sin respuesta".
                if not content.strip():
                    if previous_tool_calls:
                        content = await self._force_final_answer(messages)
                    else:
                        content = "No generé una respuesta. ¿Puedes reformular la tarea o darme más detalle?"
                await emit({
                    "event_type": "chat_response",
                    "payload": {
                        "content": content,
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

                # Loop guard: detectar repeticion exacta de tool+args
                call_key = f"{name}:{json.dumps(args, sort_keys=True)}"
                if call_key in previous_tool_calls and iteration > 0:
                    await emit({
                        "event_type": "chat_response",
                        "payload": {
                            "content": f"Detecte que estoy repitiendo la misma accion ({name}). Me detengo para no gastar tokens.",
                            "model": self.model,
                        },
                    })
                    return
                previous_tool_calls.add(call_key)

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

        # Alcanzó max_iterations sin que el modelo cerrara: en vez de rendirse y
        # tirar todo lo investigado (gasta tokens sin entregar), forzar una
        # síntesis final SIN herramientas con lo que ya reunió.
        content = await self._force_final_answer(messages)
        await emit({
            "event_type": "chat_response",
            "payload": {"content": content, "model": self.model},
        })

    async def _force_final_answer(self, messages: list[dict]) -> str:
        """Fuerza una respuesta final del modelo SIN herramientas, para no tirar el
        trabajo cuando exploró pero no cerró (contenido vacío o max_iterations).
        Convierte 'gasté tokens sin entregar' en una respuesta real con lo reunido."""
        nudge = messages + [{
            "role": "user",
            "content": (
                "Ya reuniste suficiente contexto con las herramientas. Da AHORA tu "
                "respuesta o análisis final EN TEXTO, con lo que tienes. No uses más "
                "herramientas."
            ),
        }]
        try:
            resp = await self._chat(nudge, tools=None)
            content = (resp.get("content") or "").strip()
        except Exception:
            content = ""
        return content or (
            "Reuní contexto pero no logré sintetizar una respuesta. Dame una "
            "instrucción más específica y lo intento de nuevo."
        )

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
