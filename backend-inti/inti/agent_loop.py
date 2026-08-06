"""AgentLoop — núcleo del agente Inti con tool-calling iterativo."""

import json
import re
import asyncio
import subprocess
from pathlib import Path
from typing import Callable, Awaitable

from inti.openrouter_client import openrouter
from inti.config import settings
from inti.guardrails import guardrail_engine
from inti.tools import registry as tool_registry, register_builtin_tools

# System prompt cargado desde archivo externo (versionable, A/B test)
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system.md"
if _PROMPT_PATH.exists():
    SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = """Tu nombre es Inti. Eres el agente de Dopa Code. Español neutro LATAM (tú, nunca vos). Ante comandos de acción SIEMPRE usas herramientas."""

# Streaming tools: names que manejan su propio framing
_STREAMING_TOOLS = {"run_opencode", "generate_image"}


class AgentLoop:
    def __init__(self, workspace: str, model: str | None = None, project_id: str | None = None, profile: str | None = None, require_approval: bool = False, allowed_dirs: list[str] | None = None, use_heavy_model: bool = False, tenant_id: str | None = None):
        self.workspace = Path(workspace).resolve()
        self.model = model or (settings.heavy_model if use_heavy_model else settings.loop_model)
        self.heavy_model = settings.heavy_model
        self.use_heavy_model = use_heavy_model
        self.project_id = project_id
        self.profile = profile
        self.require_approval = require_approval
        self.max_iterations = settings.max_iterations
        self.allowed_dirs = [Path(d).resolve() for d in (allowed_dirs or []) if Path(d).is_dir()]
        self.tenant_id = tenant_id
        # Registrar tools si no estan ya
        if not tool_registry.names():
            register_builtin_tools(
                self.workspace,
                self._resolve_path,
                self._check_guardrails,
            )

    def _strip_tool_text(self, content: str) -> str:
        """Remueve JSON/XML de tool calls del texto visible."""
        # Bloque JSON con fences (```json ... ```)
        content = re.sub(r'```(?:json|plaintext)?\s*\n?\{[\s\S]*?\}\s*\n?```', '', content)
        # JSON con "type": "function" (formato nativo)
        content = re.sub(r'\n?(?:json\s+)?\{[\s\S]*?"type"\s*:\s*"function"[\s\S]*?\}', '', content)
        # JSON con "function" y "parameters" (formato alternativo de DeepSeek)
        content = re.sub(r'\n?(?:json\s+)?\{(?:[^{}]*?"function"\s*:\s*"[^"]+"[^{}]*?"parameters"\s*:\s*\{[^{}]*?\}[^{}]*?|[^{}]*?"parameters"\s*:\s*\{[^{}]*?\}[^{}]*?"function"\s*:\s*"[^"]+")[^{}]*?\}', '', content)
        # Cualquier bloque JSON que empiece con { y contenga nombres de tools conocidos
        content = re.sub(r'\n?(?:json\s+)?\{[^}]*?"(?:path|content|command|task|prompt|key|value)"[^}]*?\}', '', content)
        # Residuos: lineas con solo } o json sueltos, o JSON parcial
        content = re.sub(r'^\s*(?:json|\}|"function"|"parameters")\s*$', '', content, flags=re.MULTILINE)
        # Colapsar lineas vacias multiples
        content = re.sub(r'\n{3,}', '\n\n', content)
        # XML tool calls
        content = re.sub(r"<tool_calls>[\s\S]*?</tool_calls>", "", content)
        content = re.sub(rf"<(?:[\w-]+:)?(list_dir|read_file|write_file|run_command|git_diff|run_opencode|web_fetch|save_memory|recall_memory|generate_image)\b[^>]*\s*/>", "", content)
        return content.strip()

    def _make_clean_content(self, raw: str, tool_calls: list[dict] | None) -> str:
        """Genera contenido limpio. Si hay tool_calls, solo muestra un resumen."""
        if not tool_calls:
            return self._strip_tool_text(raw)
        names = [tc["function"]["name"] for tc in tool_calls if tc.get("function", {}).get("name")]
        args_list = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            n = fn.get("name", "")
            try:
                a = json.loads(fn.get("arguments", "{}"))
            except Exception:
                a = {}
            arg = a.get("path") or a.get("command") or a.get("task") or ""
            args_list.append(f"{n}({arg[:40]})" if arg else n)
        return "Usando: " + ", ".join(args_list[:8]) if args_list else ""

    def _parse_xml_tool_calls(self, content: str) -> tuple[list[dict] | None, str]:
        """Si el LLM responde con <tool_calls><invoke>..., parsear a tool_calls nativos."""
        import uuid
        import html as html_mod
        import re as re_xml
        tool_calls = []
        # Unescape HTML entities que DeepSeek a veces mete
        unescaped = html_mod.unescape(content)
        # Parse <tool_calls> o <aze:tool_calls> con opcional namespace prefix
        ns = r'(?:[\w-]+:)?'  # opcional: aze:, etc.
        invoke_pattern = re_xml.compile(rf'<{ns}invoke\s+name="(\w+)"[^>]*>(.*?)</{ns}invoke>', re_xml.DOTALL)
        param_pattern = re_xml.compile(rf'<{ns}parameter\s+name="(\w+)"[^>]*>(.*?)</{ns}parameter>', re_xml.DOTALL)
        clean = unescaped
        for m in invoke_pattern.finditer(unescaped):
            name = m.group(1)
            body = m.group(2)
            args = {}
            for pm in param_pattern.finditer(body):
                args[pm.group(1)] = pm.group(2).strip()
            tool_calls.append({
                "id": f"xml_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            })
        if tool_calls:
            # Limpiar el XML del contenido (con o sin namespace)
            clean = re.sub(rf"<{ns}tool_calls>[\s\S]*?</{ns}tool_calls>", "", unescaped)
            clean = re.sub(rf"<{ns}(list_dir|read_file|write_file|run_command|git_diff|run_opencode|web_fetch|save_memory|recall_memory|generate_image)\b[^>]*\s*/>", "", clean)
            clean = clean.strip()
            return tool_calls, clean
        return None, content

    def _resolve_path(self, path: str) -> Path:
        """Resuelve una ruta relativa al workspace y verifica que no escape.

        Usa is_relative_to (no startswith) para que un directorio hermano con
        prefijo común — p.ej. workspace `.../ws` y ruta `../ws-evil/x` — NO pase
        el check por coincidencia de string. Tambien permite allowed_dirs."""
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
                # DeepSeek ignora function calling nativo → no enviar tools
                resp = await multiprovider.chat("deepseek", self.model, messages, 4000)
                if "error" not in resp and resp.get("content"):
                    return resp
                if "error" not in resp:
                    resp2 = await multiprovider.chat("deepseek", self.model, messages, 4000)
                    if "error" not in resp2 and resp2.get("content"):
                        return resp2
        # Fallback a OpenRouter
        return await openrouter.chat(self.model, messages, tools=tools)

    async def _chat_stream(self, emit, messages: list[dict], tools: list[dict]) -> dict:
        """Streaming: emite tokens paso a paso. Devuelve el resultado final."""
        if "deepseek" in self.model and "deepseek/deepseek" not in self.model:
            from inti.config import settings
            from inti.openrouter_client import multiprovider
            key = multiprovider.providers.get("deepseek") or settings.deepseek_api_key
            if key:
                final_resp = {}
                # DeepSeek ignora function calling → no enviar tools, el prompt las describe
                async for chunk in multiprovider.chat_stream("deepseek", self.model, messages, 4000):
                    if "error" in chunk:
                        return chunk
                    if "token" in chunk:
                        await emit({
                            "event_type": "stream.token",
                            "data": {"text": chunk["token"]},
                        })
                    if "content" in chunk:
                        final_resp = chunk
                return final_resp
        # Fallback no-streaming
        try:
            return await self._chat(messages, tools)
        except Exception as e:
            return {"error": f"OpenRouter _chat failed: {str(e)}"}

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
        """Ejecuta una herramienta via el ToolRegistry."""
        return await tool_registry.execute(name, args, emit=emit)

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
        BRIDGE_TOKEN = settings.bridge_token or "dopa-bridge-local-dev"

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
                system_content = system_content + "\n\n" + mem
        except Exception:
            pass

        # Inyectar contexto ERP si hay tenant_id (Dopa CRM/DopaWeb)
        if self.tenant_id:
            try:
                from inti.erp_context import erp_context as ec
                ctx = await ec.build_prompt_context(self.tenant_id)
                if ctx:
                    system_content = system_content + "\n\n" + ctx
            except Exception:
                pass

        messages = [
            {"role": "system", "content": system_content},
            *(history or []),
            {"role": "user", "content": user_message},
        ]

        previous_tool_calls: set[str] = set()  # Guard contra repeticion
        nudge_count = 0  # Contador de nudges sin tools

        for iteration in range(self.max_iterations):
            # Emitir "pensando" en CADA iteracion para que el usuario sepa que Inti sigue vivo
            await emit({
                "event_type": "loop.thinking",
                "payload": {"iteration": iteration + 1, "max": self.max_iterations},
            })
            # Routing: DeepSeek directo (sin OpenRouter markup) o OpenRouter
            try:
                resp = await self._chat_stream(emit, messages, tool_registry.schemas())
            except Exception as chat_err:
                    await emit({
                        "event_type": "error",
                        "payload": {"error": f"Error de conexion LLM: {str(chat_err)[:200]}"},
                    })
                    return

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
            # Si el modelo devuelve tool calls como texto XML en vez del formato nativo
            if not tool_calls and resp.get("content"):
                parsed_tc, clean_content = self._parse_xml_tool_calls(resp["content"])
                if parsed_tc:
                    resp["content"] = clean_content
                    tool_calls = parsed_tc
                    # Emitir el texto limpio antes de ejecutar tools (limpia el streaming)
                    if clean_content:
                        await emit({
                            "event_type": "chat_response",
                            "payload": {"content": clean_content, "model": self.model},
                        })
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
                content = self._strip_tool_text(resp.get("content", "") or "")
                # Si el contenido es puro JSON o vacio after strip
                if content.strip().startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                    if len(content) < 20:
                        content = "Procesando tu solicitud. Intentemos algo mas especifico."
                # Si es respuesta conversacional a comando de acción → nudge (max 3)
                is_action = any(w in user_message.lower() for w in ["audita","analiza","revisa","diagnostica","crea","genera","escribe","modifica","arregla","corrige","implementa","desarrolla","codifica","refactoriza","hace","haz","construye","diseña","despliega"])
                if not previous_tool_calls and is_action and len(content) < 800:
                    nudge_count += 1
                    if nudge_count > 3:
                        content = await self._force_final_answer(messages)
                    else:
                        messages.append({"role": "user", "content": "USA HERRAMIENTAS YA. No describas, no preguntes. Usa list_dir, read_file, write_file. Ejecuta."})
                        continue
                # Si ya uso tools pero responde sin sustancia → forzar sintesis
                if previous_tool_calls and len(content) < 200 and not content.startswith("No gener"):
                    content = await self._force_final_answer(messages)
                # Contenido vacío → forzar síntesis
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
                "content": self._make_clean_content(resp.get("content") or "", tool_calls),
                "tool_calls": tool_calls,
            })

            # Ejecutar tools: read-only en paralelo, write/run en secuencia
            READ_TOOLS = {"read_file", "list_dir", "git_diff"}
            read_tasks: list[tuple[int, dict, str, dict]] = []
            write_tasks: list[tuple[int, dict, str, dict]] = []

            for i, tc in enumerate(tool_calls):
                fn = tc["function"]
                name = fn["name"]
                try:
                    args = json.loads(fn["arguments"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}

                # Loop guard
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

                if name in READ_TOOLS:
                    read_tasks.append((i, tc, name, args))
                else:
                    write_tasks.append((i, tc, name, args))

            async def _run_read(idx: int, tc: dict, name: str, args: dict):
                await emit({"event_type": "step.start", "data": {"tool": name, "args": args}})
                result = await self.execute_tool(name, args)
                await emit({"event_type": "step.delta", "data": {"text": f"🔧 {name} → {result[:800]}"}})
                await emit({"event_type": "step.stop", "data": {"index": idx}})
                return (idx, tc, result)

            # Ejecutar reads en paralelo
            if read_tasks:
                results = await asyncio.gather(*[_run_read(i, tc, n, a) for i, tc, n, a in read_tasks])
                for idx, tc, result in sorted(results, key=lambda x: x[0]):
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

            # Ejecutar writes/commands en secuencia
            for idx, tc, name, args in write_tasks:
                await emit({"event_type": "step.start", "data": {"tool": name, "args": args}})
                result = await self.execute_tool(name, args)
                await emit({"event_type": "step.delta", "data": {"text": f"🔧 {name} → {result[:800]}"}})
                await emit({"event_type": "step.stop", "data": {"index": idx}})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

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
        # Des-staging para que git status siga mostrando cambios (pestana Cambios)
        subprocess.run(["git", "reset", "HEAD"], cwd=ws, capture_output=True, text=True)
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
