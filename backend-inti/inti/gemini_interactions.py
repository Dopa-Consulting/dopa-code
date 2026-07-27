"""
Gemini Interactions API - Cliente real (GA Junio 2026).

Formato correcto segun la documentacion oficial:
  - input: array de content objects [{type: "text", text: "..."}]
  - response: steps[] con model_output, thought, function_call
  - previous_interaction_id para multi-turn
  - background=true para tareas largas
  - agent en vez de model para agentes (Antigravity, Deep Research)

API keys nuevas: formato AQ.A... (antes AIza...).
"""

import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from inti.config import settings

logger = logging.getLogger("inti.gemini_interactions")

INTERACTIONS_API = "https://generativelanguage.googleapis.com/v1beta"

# Prefijos validos de Google API key.
#   AQ.  -> formato nuevo (GA 2026)
#   AIza -> formato clasico (Google AI Studio)
GOOGLE_KEY_PREFIXES = ("AQ.", "AIza")


def is_valid_google_key(key: str) -> bool:
    """True si la key no esta vacia, no es un placeholder y tiene prefijo valido."""
    if not key or key.endswith("..."):
        return False
    return key.startswith(GOOGLE_KEY_PREFIXES)


INTERACTIONS_MODELS = {
    "gemini-3.6-flash": {
        "name": "Gemini 3.6 Flash", "type": "model",
        "pricing": {"prompt": 0.40, "completion": 2.00},
        "capabilities": ["code", "agentic", "multimodal", "fast"],
    },
    "gemini-3.5-flash": {
        "name": "Gemini 3.5 Flash", "type": "model",
        "pricing": {"prompt": 0.30, "completion": 1.50},
        "capabilities": ["code", "agentic", "reasoning"],
    },
    "gemini-3.1-pro-preview": {
        "name": "Gemini 3.1 Pro", "type": "model",
        "pricing": {"prompt": 1.25, "completion": 10.00},
        "capabilities": ["reasoning", "code", "agentic"],
    },
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash", "type": "model",
        "pricing": {"prompt": 0.15, "completion": 0.60},
        "capabilities": ["code", "multimodal", "fast", "cheap"],
    },
    "gemini-3.1-flash-image": {
        "name": "Nano Banana 2", "type": "model",
        "pricing": {"prompt": 2.00, "completion": 0},
        "capabilities": ["image", "generation", "editing"],
    },
    "deep-research-preview-04-2026": {
        "name": "Deep Research", "type": "agent",
        "pricing": {"prompt": 5.00, "completion": 25.00},
        "capabilities": ["research", "autonomous", "web-search"],
    },
    "antigravity-preview-05-2026": {
        "name": "Antigravity Agent", "type": "agent",
        "pricing": {"prompt": 2.00, "completion": 8.00},
        "capabilities": ["autonomous", "code", "sandbox", "browser"],
    },
}


class GeminiInteractions:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.google_api_key
        self.base_url = INTERACTIONS_API
        self.last_interaction_id: str | None = None

    @property
    def is_configured(self) -> bool:
        return is_valid_google_key(self.api_key)

    # ------------------------------------------------------------------
    # Core: interact (sincrono)
    # ------------------------------------------------------------------

    async def interact(
        self,
        model: str = "",
        agent: str = "",
        user_input: str = "",
        system_instruction: str | None = None,
        tools: list[dict] | None = None,
        background: bool = False,
        store: bool = True,
        previous_interaction_id: str | None = None,
    ) -> dict:
        if not self.is_configured:
            return {"error": "DOPA_GOOGLE_API_KEY not configured"}

        if settings.dopa_code_dummy:
            return {"output": f"[DUMMY] {model or agent}: {user_input[:100]}..."}

        payload: dict = {
            "input": user_input,  # string directly, not array of parts
            "store": store,
        }

        if model:
            payload["model"] = model
        if agent:
            payload["agent"] = agent
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}
        if tools:
            payload["tools"] = tools
        if background:
            payload["background"] = True
        if previous_interaction_id or self.last_interaction_id:
            payload["previous_interaction_id"] = previous_interaction_id or self.last_interaction_id

        try:
            async with httpx.AsyncClient(timeout=300.0 if background else 120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/interactions",
                    headers={
                        "x-goog-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if resp.status_code != 200:
                    return {"error": f"API error {resp.status_code}", "detail": resp.text[:500]}

                data = resp.json()
                if data.get("id"):
                    self.last_interaction_id = data["id"]

                return {
                    "id": data.get("id"),
                    "status": data.get("status"),
                    "model": data.get("model") or data.get("agent"),
                    "output": self._output_text(data),
                    "steps": self._steps_summary(data),
                    "usage": data.get("usage", {}),
                    "requires_action": data.get("status") == "requires_action",
                }
        except httpx.ConnectError:
            return {"error": "Cannot reach Gemini API"}
        except httpx.TimeoutException:
            return {"error": "Timeout"}

    # ------------------------------------------------------------------
    # Streaming (SSE step-by-step)
    # ------------------------------------------------------------------

    async def interact_stream(
        self, model: str = "", agent: str = "", user_input: str = "",
        system_instruction: str | None = None,
    ) -> AsyncIterator[dict]:
        if not self.is_configured:
            yield {"event_type": "error", "data": {"error": "API key not configured"}}
            return

        payload: dict = {
            "input": user_input,  # string directly
            "stream": True,
        }
        if model:
            payload["model"] = model
        if agent:
            payload["agent"] = agent
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/interactions",
                    headers={
                        "x-goog-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        d = line[6:].strip()
                        if d == "[DONE]":
                            yield {"event_type": "done", "data": {}}
                            break
                        try:
                            event = json.loads(d)
                            ev = event.get("event_type", "unknown")

                            if ev == "interaction.created":
                                self.last_interaction_id = event.get("interaction", {}).get("id")
                                yield {"event_type": ev, "data": event}

                            elif ev == "step.start":
                                step = event.get("step", {})
                                yield {"event_type": ev, "data": {"index": event.get("index"), "type": step.get("type")}}

                            elif ev == "step.delta":
                                delta = event.get("delta", {})
                                yield {
                                    "event_type": ev,
                                    "data": {
                                        "index": event.get("index"),
                                        "delta_type": delta.get("type", "unknown"),
                                        "text": delta.get("text", ""),
                                    }
                                }

                            elif ev == "step.stop":
                                yield {"event_type": ev, "data": {"index": event.get("index")}}

                            elif ev in ("interaction.completed", "interaction.status_update"):
                                yield {"event_type": ev, "data": event}

                            else:
                                yield {"event_type": ev, "data": event}
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield {"event_type": "error", "data": {"error": str(e)}}

    # ------------------------------------------------------------------
    # Specialized
    # ------------------------------------------------------------------

    async def deep_research(self, query: str) -> dict:
        return await self.interact(
            agent="deep-research-preview-04-2026",
            user_input=query,
            background=True,
        )

    async def antigravity_qa(self, code: str, context: str = "") -> dict:
        prompt = f"Context: {context}\n\nReview this code for bugs, security, and best practices:\n\n{code}" if context else code
        return await self.interact(
            agent="antigravity-preview-05-2026",
            user_input=prompt,
        )

    async def continue_chat(self, user_input: str, previous_id: str = "") -> dict:
        return await self.interact(
            model="gemini-2.5-flash",
            user_input=user_input,
            previous_interaction_id=previous_id or self.last_interaction_id,
        )

    async def get_interaction(self, interaction_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/interactions/{interaction_id}",
                    headers={"x-goog-api-key": self.api_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"status": data.get("status"), "output": self._output_text(data)}
                return {"error": f"Get failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _output_text(self, data: dict) -> str:
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                for block in step.get("content", []):
                    if block.get("type") == "text":
                        return block.get("text", "")
        return ""

    def _steps_summary(self, data: dict) -> list[dict]:
        return [
            {"type": s.get("type"), "content_types": [c.get("type") for c in s.get("content", [])]}
            for s in data.get("steps", [])
        ]


gemini_interactions = GeminiInteractions()
