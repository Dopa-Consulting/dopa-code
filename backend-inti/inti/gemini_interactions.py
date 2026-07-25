"""
Gemini Interactions API - Nueva API unificada de Google (GA Junio 2026).

Reemplaza generateContent con una interfaz unica para modelos y agentes.
Beneficios:
  - Server-side state management (previous_interaction_id)
  - Background execution para tareas largas (background=true)
  - Observable execution steps (tool calls, model thoughts, outputs)
  - Implicit caching que reduce costos de token
  - Mismo endpoint para modelos Y agentes (Deep Research, Antigravity)

Endpoint: POST https://generativelanguage.googleapis.com/v1/models/{model}:interactions

Para Dopa Code:
  - Inti usa Interactions API para sesiones multi-turn (cache implicito)
  - Deep Research agent para la fase de investigacion del Architect
  - Antigravity agent nativo para QA (sin API separada)
  - Background execution para pipelines largos (planning + execution)
"""

import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from inti.config import settings

logger = logging.getLogger("inti.gemini_interactions")

INTERACTIONS_API = "https://generativelanguage.googleapis.com/v1"

INTERACTIONS_MODELS = {
    "gemini-3.6-flash": {
        "name": "Gemini 3.6 Flash",
        "type": "model",
        "context_length": 1048576,
        "pricing": {"prompt": 0.40, "completion": 2.00},
        "capabilities": ["code", "agentic", "multimodal", "fast"],
        "supports_background": True,
    },
    "gemini-3.5-flash": {
        "name": "Gemini 3.5 Flash",
        "type": "model",
        "context_length": 1048576,
        "pricing": {"prompt": 0.30, "completion": 1.50},
        "capabilities": ["code", "agentic", "reasoning"],
        "supports_background": True,
    },
    "gemini-3.1-pro-preview": {
        "name": "Gemini 3.1 Pro",
        "type": "model",
        "context_length": 1048576,
        "pricing": {"prompt": 1.25, "completion": 10.00},
        "capabilities": ["reasoning", "code", "agentic", "multimodal"],
        "supports_background": True,
    },
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "type": "model",
        "context_length": 1048576,
        "pricing": {"prompt": 1.25, "completion": 10.00},
        "capabilities": ["reasoning", "code", "multimodal"],
        "supports_background": True,
    },
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "type": "model",
        "context_length": 1048576,
        "pricing": {"prompt": 0.15, "completion": 0.60},
        "capabilities": ["code", "multimodal", "fast", "cheap"],
        "supports_background": True,
    },
    # Agents
    "deep-research-preview-04-2026": {
        "name": "Deep Research",
        "type": "agent",
        "context_length": 1048576,
        "pricing": {"prompt": 5.00, "completion": 25.00},
        "capabilities": ["research", "autonomous", "web-search", "reporting"],
        "supports_background": True,
    },
    "deep-research-max-preview-04-2026": {
        "name": "Deep Research Max",
        "type": "agent",
        "context_length": 1048576,
        "pricing": {"prompt": 10.00, "completion": 50.00},
        "capabilities": ["research", "deep", "exhaustive", "web-search"],
        "supports_background": True,
    },
    "antigravity-preview-05-2026": {
        "name": "Antigravity Agent",
        "type": "agent",
        "context_length": 1048576,
        "pricing": {"prompt": 2.00, "completion": 8.00},
        "capabilities": ["autonomous", "code", "sandbox", "browser"],
        "supports_background": True,
    },
}


class GeminiInteractions:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.google_api_key
        self.base_url = INTERACTIONS_API
        self.last_interaction_id: str | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def interact(
        self,
        model: str,
        user_input: str | list,
        system_instruction: str | None = None,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        background: bool = False,
        store: bool = True,
    ) -> dict:
        """
        Crear una nueva interaccion (turno de conversacion).
        Soporta modelos y agentes con el mismo endpoint.
        """
        if not self.is_configured:
            return {"error": "Google API key not configured"}

        if settings.dopa_code_dummy:
            return self._dummy_interaction(model, user_input)

        parts = []
        if isinstance(user_input, str):
            parts = [{"text": user_input}]
        else:
            parts = user_input

        payload = {
            "user_input": {"parts": parts},
            "store": store,
        }

        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        if tools:
            payload["tools"] = tools

        if temperature is not None:
            payload["generation_config"] = {"temperature": temperature}

        if background:
            payload["background"] = True

        if self.last_interaction_id:
            payload["previous_interaction_id"] = self.last_interaction_id

        try:
            async with httpx.AsyncClient(timeout=300.0 if background else 120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/models/{model}:interactions",
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )

                if resp.status_code == 202:
                    return {
                        "status": "background",
                        "model": model,
                        "message": "Task running in background",
                    }

                if resp.status_code != 200:
                    return {
                        "error": f"Interactions API error {resp.status_code}",
                        "detail": resp.text[:500],
                    }

                data = resp.json()

                if data.get("id"):
                    self.last_interaction_id = data["id"]

                return {
                    "model": model,
                    "interaction_id": data.get("id"),
                    "output": self._extract_output(data),
                    "steps": self._extract_steps(data),
                    "usage": self._extract_usage(data),
                }

        except httpx.ConnectError:
            return {"error": "Cannot reach Gemini Interactions API"}
        except httpx.TimeoutException:
            return {"error": "Interactions API timed out"}

    async def interact_stream(
        self, model: str, user_input: str, system_instruction: str | None = None
    ) -> AsyncIterator[dict]:
        """
        Streaming con step-based events (SSE).
        Eventos: interaction.created → step.start → step.delta → step.stop → interaction.completed
        Soporta: text, thought_summary, function_call, image, google_search.
        """
        if not self.is_configured:
            yield {"event_type": "error", "payload": {"error": "API key not configured"}}
            return

        payload: dict = {
            "user_input": {"parts": [{"text": user_input}]},
            "stream": True,
        }
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/models/{model}:interactions",
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield {"event_type": "done", "payload": {}}
                            break
                        try:
                            data = json.loads(data_str)
                            event_type = data.get("event_type", "unknown")

                            if event_type == "interaction.created":
                                self.last_interaction_id = data.get("interaction", {}).get("id")
                                yield {"event_type": "interaction.created", "payload": data}

                            elif event_type == "step.start":
                                step = data.get("step", {})
                                yield {
                                    "event_type": "step.start",
                                    "payload": {
                                        "index": data.get("index", 0),
                                        "step_type": step.get("type", "unknown"),
                                        "step_name": step.get("name", ""),
                                    }
                                }

                            elif event_type == "step.delta":
                                delta = data.get("delta", {})
                                delta_type = delta.get("type", "unknown")
                                out: dict = {
                                    "event_type": "step.delta",
                                    "payload": {"index": data.get("index", 0), "delta_type": delta_type},
                                }

                                if delta_type == "text":
                                    out["payload"]["text"] = delta.get("text", "")
                                elif delta_type == "thought_summary":
                                    content = delta.get("content", {})
                                    out["payload"]["text"] = content.get("text", "")
                                    out["payload"]["delta_type"] = "thinking"
                                elif delta_type == "image":
                                    out["payload"]["data"] = delta.get("data", "")[:50] + "..."
                                    out["payload"]["mime_type"] = delta.get("mime_type", "")
                                elif delta_type == "arguments_delta":
                                    out["payload"]["arguments"] = delta.get("arguments", "")
                                elif delta_type == "google_search_call":
                                    out["payload"]["queries"] = delta.get("arguments", {})
                                elif delta_type == "thought_signature":
                                    out["payload"]["delta_type"] = "thinking_signature"

                                yield out

                            elif event_type == "step.stop":
                                yield {
                                    "event_type": "step.stop",
                                    "payload": {"index": data.get("index", 0)}
                                }

                            elif event_type == "interaction.completed":
                                usage = data.get("interaction", {}).get("usage", {})
                                yield {
                                    "event_type": "interaction.completed",
                                    "payload": {
                                        "status": data.get("interaction", {}).get("status"),
                                        "total_tokens": usage.get("total_tokens", 0),
                                        "cached_tokens": usage.get("total_cached_tokens", 0),
                                    }
                                }

                            elif event_type == "error":
                                yield {"event_type": "error", "payload": data.get("error", {})}

                            else:
                                yield {"event_type": event_type, "payload": data}

                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield {"event_type": "error", "payload": {"error": str(e)}}

    async def continue_interaction(
        self,
        model: str,
        user_input: str,
        previous_interaction_id: str | None = None,
    ) -> dict:
        """Continua una conversacion usando el previous_interaction_id."""
        pid = previous_interaction_id or self.last_interaction_id
        if not pid:
            return {"error": "No previous interaction to continue"}

        payload = {
            "user_input": {"parts": [{"text": user_input}]},
            "previous_interaction_id": pid,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/models/{model}:interactions",
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code != 200:
                    return {"error": f"API error {resp.status_code}"}
                data = resp.json()
                if data.get("id"):
                    self.last_interaction_id = data["id"]
                return {
                    "model": model,
                    "interaction_id": data.get("id"),
                    "output": self._extract_output(data),
                }
        except Exception as e:
            return {"error": str(e)}

    async def deep_research(self, query: str, max_mode: bool = False) -> dict:
        """Usa el Deep Research agent para investigacion autonoma."""
        model = "deep-research-max-preview-04-2026" if max_mode else "deep-research-preview-04-2026"
        return await self.interact(
            model=model,
            user_input=query,
            system_instruction="Investigate thoroughly and produce a comprehensive report with citations.",
            background=True,
        )

    async def antigravity_qa(self, code_or_diff: str, context: str = "") -> dict:
        """Usa el Antigravity agent para QA de codigo."""
        return await self.interact(
            model="antigravity-preview-05-2026",
            user_input=[
                {"text": f"Context: {context}\n\nCode to review:\n{code_or_diff}"}
            ],
            system_instruction=(
                "You are a QA agent. Review the code for bugs, security issues, "
                "performance problems, and adherence to best practices. "
                "Provide a structured report with severity levels."
            ),
        )

    async def get_interaction(self, interaction_id: str) -> dict:
        """Recupera una interaccion almacenada."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/interactions/{interaction_id}",
                    params={"key": self.api_key},
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"Get failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    async def delete_interaction(self, interaction_id: str) -> dict:
        """Elimina una interaccion almacenada."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    f"{self.base_url}/interactions/{interaction_id}",
                    params={"key": self.api_key},
                )
                if resp.status_code == 200:
                    return {"status": "deleted", "interaction_id": interaction_id}
                return {"error": f"Delete failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def _extract_output(self, data: dict) -> str:
        """Extrae el texto de salida de la respuesta."""
        try:
            parts = data.get("model_output", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if "text" in p)
        except Exception:
            return ""

    def _extract_steps(self, data: dict) -> list[dict]:
        """Extrae los execution steps para debugging/UI."""
        steps = []
        try:
            for step in data.get("execution_steps", []):
                steps.append({
                    "step_type": step.get("step_type", "unknown"),
                    "summary": step.get("summary", ""),
                    "tool_call": step.get("function_call", {}).get("name", ""),
                })
        except Exception:
            pass
        return steps

    def _extract_usage(self, data: dict) -> dict:
        """Extrae el token usage."""
        try:
            usage = data.get("usage_metadata", {})
            return {
                "prompt_tokens": usage.get("prompt_token_count", 0),
                "candidates_tokens": usage.get("candidates_token_count", 0),
                "total_tokens": usage.get("total_token_count", 0),
                "cached_tokens": usage.get("cached_content_token_count", 0),
            }
        except Exception:
            return {}

    def _dummy_interaction(self, model: str, user_input) -> dict:
        text = user_input if isinstance(user_input, str) else str(user_input)
        return {
            "model": model,
            "interaction_id": f"dummy-{datetime.now(timezone.utc).timestamp()}",
            "output": f"[DUMMY] Interaction response for: {text[:100]}...",
            "steps": [{"step_type": "model_output", "summary": "Dummy response"}],
            "usage": {"total_tokens": 150, "cached_tokens": 50},
        }


gemini_interactions = GeminiInteractions()
