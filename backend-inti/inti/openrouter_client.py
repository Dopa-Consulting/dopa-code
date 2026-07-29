import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from inti.config import settings

logger = logging.getLogger("inti.openrouter")

OPENROUTER_API = "https://openrouter.ai/api/v1"

OPENROUTER_MODELS = {
    "anthropic/claude-opus-4-8": {
        "name": "Claude Opus 4.8",
        "provider": "Anthropic",
        "context_length": 200000,
        "max_output": 32000,
        "pricing": {
            "prompt": 15.00,
            "completion": 75.00,
        },
        "capabilities": ["reasoning", "code", "architecture", "planning"],
        "free": False,
    },
    "anthropic/claude-sonnet-5": {
        "name": "Claude Sonnet 5",
        "provider": "Anthropic",
        "context_length": 200000,
        "max_output": 8192,
        "pricing": {
            "prompt": 3.00,
            "completion": 15.00,
        },
        "capabilities": ["code", "reasoning", "fast"],
        "free": False,
    },
    "deepseek/deepseek-chat": {
        "name": "DeepSeek V4",
        "provider": "DeepSeek",
        "context_length": 128000,
        "max_output": 8192,
        "pricing": {
            "prompt": 0.14,
            "completion": 0.28,
        },
        "capabilities": ["code", "fast", "cheap"],
        "free": False,
    },
    "deepseek/deepseek-r1": {
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "context_length": 128000,
        "max_output": 8192,
        "pricing": {
            "prompt": 0.55,
            "completion": 2.19,
        },
        "capabilities": ["reasoning", "code", "math"],
        "free": False,
    },
    "google/gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {
            "prompt": 0.15,
            "completion": 0.60,
        },
        "capabilities": ["code", "multimodal", "fast", "cheap"],
        "free": False,
    },
    "google/gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {"prompt": 1.25, "completion": 10.00},
        "capabilities": ["reasoning", "code", "multimodal"],
        "free": False,
    },
    # Gemini 3.x (via Google AI directa)
    "google/gemini-3.1-flash-lite": {
        "name": "Gemini 3.1 Flash-Lite",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {"prompt": 0.10, "completion": 0.40},
        "capabilities": ["code", "fast", "cheap", "multimodal"],
        "free": False,
    },
    "google/gemini-3.1-pro-preview": {
        "name": "Gemini 3.1 Pro",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {"prompt": 1.25, "completion": 10.00},
        "capabilities": ["reasoning", "code", "agentic", "multimodal"],
        "free": False,
    },
    "google/gemini-3.5-flash": {
        "name": "Gemini 3.5 Flash",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {"prompt": 0.30, "completion": 1.50},
        "capabilities": ["reasoning", "code", "agentic", "multimodal"],
        "free": False,
    },
    "google/gemini-3.6-flash": {
        "name": "Gemini 3.6 Flash",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {"prompt": 0.40, "completion": 2.00},
        "capabilities": ["reasoning", "code", "agentic", "multimodal", "fast"],
        "free": False,
    },
    # Gemini Live / Voice models (via Google AI directa)
    "google/gemini-3.1-flash-live": {
        "name": "Gemini 3.1 Flash Live",
        "provider": "Google",
        "context_length": 32768,
        "max_output": 4096,
        "pricing": {"prompt": 0.50, "completion": 2.00},
        "capabilities": ["voice", "live", "realtime", "multimodal"],
        "free": False,
    },
    "google/gemini-2.5-flash-native-audio": {
        "name": "Gemini 2.5 Flash Live",
        "provider": "Google",
        "context_length": 32768,
        "max_output": 4096,
        "pricing": {"prompt": 0.30, "completion": 1.50},
        "capabilities": ["voice", "live", "audio", "multimodal"],
        "free": False,
    },
    # TTS models (via Google AI directa)
    "google/gemini-3.1-flash-tts": {
        "name": "Gemini 3.1 Flash TTS",
        "provider": "Google",
        "context_length": 8192,
        "max_output": 4096,
        "pricing": {"prompt": 0.20, "completion": 1.00},
        "capabilities": ["tts", "speech", "voice"],
        "free": False,
    },
    "google/gemini-2.5-flash-tts": {
        "name": "Gemini 2.5 Flash TTS",
        "provider": "Google",
        "context_length": 8192,
        "max_output": 4096,
        "pricing": {"prompt": 0.15, "completion": 0.80},
        "capabilities": ["tts", "speech", "voice", "fast"],
        "free": False,
    },
    # Image generation models (via Google AI directa)
    "google/nano-banana-2": {
        "name": "Nano Banana 2",
        "provider": "Google",
        "context_length": 4096,
        "max_output": 4096,
        "pricing": {"prompt": 2.00, "completion": 0},
        "capabilities": ["image", "generation", "editing", "fast"],
        "free": False,
    },
    "google/nano-banana-2-lite": {
        "name": "Nano Banana 2 Lite",
        "provider": "Google",
        "context_length": 4096,
        "max_output": 4096,
        "pricing": {"prompt": 1.00, "completion": 0},
        "capabilities": ["image", "generation", "editing", "cheap"],
        "free": False,
    },
    "google/nano-banana-pro": {
        "name": "Nano Banana Pro",
        "provider": "Google",
        "context_length": 8192,
        "max_output": 4096,
        "pricing": {"prompt": 5.00, "completion": 0},
        "capabilities": ["image", "generation", "editing", "4k", "precise"],
        "free": False,
    },
    "google/gemini-2.5-flash-image": {
        "name": "Nano Banana (2.5 Flash Image)",
        "provider": "Google",
        "context_length": 4096,
        "max_output": 4096,
        "pricing": {"prompt": 1.50, "completion": 0},
        "capabilities": ["image", "generation", "editing", "creative"],
        "free": False,
    },
    "openai/gpt-4.1": {
        "name": "GPT-4.1",
        "provider": "OpenAI",
        "context_length": 128000,
        "max_output": 16384,
        "pricing": {
            "prompt": 2.00,
            "completion": 8.00,
        },
        "capabilities": ["code", "reasoning", "general"],
        "free": False,
    },
    "meta-llama/llama-4-maverick": {
        "name": "Llama 4 Maverick",
        "provider": "Meta",
        "context_length": 131072,
        "max_output": 8192,
        "pricing": {
            "prompt": 0.20,
            "completion": 0.90,
        },
        "capabilities": ["code", "general", "open"],
        "free": False,
    },
    # --- Modelos GRATUITOS via OpenRouter ---
    "google/gemma-3-27b-it": {
        "name": "Gemma 3 27B (FREE)",
        "provider": "Google",
        "context_length": 8192,
        "max_output": 8192,
        "pricing": {"prompt": 0, "completion": 0},
        "capabilities": ["free", "code", "general"],
        "free": True,
    },
    "meta-llama/llama-4-scout": {
        "name": "Llama 4 Scout (FREE)",
        "provider": "Meta",
        "context_length": 131072,
        "max_output": 8192,
        "pricing": {"prompt": 0, "completion": 0},
        "capabilities": ["free", "code", "open"],
        "free": True,
    },
    "mistralai/mistral-small-3.1-24b": {
        "name": "Mistral Small 3.1 (FREE)",
        "provider": "Mistral",
        "context_length": 32768,
        "max_output": 8192,
        "pricing": {"prompt": 0, "completion": 0},
        "capabilities": ["free", "code", "fast"],
        "free": True,
    },
    "qwen/qwen-3-30b-a3b": {
        "name": "Qwen 3 30B (FREE)",
        "provider": "Qwen",
        "context_length": 32768,
        "max_output": 8192,
        "pricing": {"prompt": 0, "completion": 0},
        "capabilities": ["free", "code", "cheap"],
        "free": True,
    },
}


class OpenRouterClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = OPENROUTER_API

    async def load_key(self) -> str:
        from inti.database import async_session
        from inti.models.project_knowledge import ProjectKnowledge
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == "dopa",
                    ProjectKnowledge.key == "openrouter_api_key"
                )
            )
            entry = result.scalar_one_or_none()
            if entry:
                self.api_key = entry.value
                return entry.value

        if settings.openrouter_api_key:
            self.api_key = settings.openrouter_api_key
            return settings.openrouter_api_key

        return ""

    async def save_key(self, api_key: str) -> None:
        from inti.database import async_session
        from inti.models.project_knowledge import ProjectKnowledge
        from sqlalchemy import select

        self.api_key = api_key
        async with async_session() as session:
            result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == "dopa",
                    ProjectKnowledge.key == "openrouter_api_key"
                )
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.value = api_key
            else:
                entry = ProjectKnowledge(
                    project_id="dopa",
                    key="openrouter_api_key",
                    value=api_key,
                )
                session.add(entry)
            await session.commit()
        self.base_url = OPENROUTER_API

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key) and not self.api_key.endswith("...")

    def get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Dopa-Consulting/dopa-code",
            "X-Title": "Dopa Code - Inti",
        }

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8000,
        stream: bool = False,
        tools: list | None = None,
        tool_choice: str = "auto",
    ) -> dict:
        if not self.is_configured:
            return {"error": "OpenRouter API key not configured"}

        if settings.dopa_code_dummy:
            return self._dummy_chat(model, messages)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.get_headers(),
                    json=payload,
                )

                if resp.status_code != 200:
                    return {
                        "error": f"OpenRouter error {resp.status_code}",
                        "detail": resp.text[:500],
                    }

                data = resp.json()
                choice = data.get("choices", [{}])[0]
                usage = data.get("usage", {})

                return {
                    "model": data.get("model", model),
                    "content": choice.get("message", {}).get("content", ""),
                    "finish_reason": choice.get("finish_reason", "unknown"),
                    "tool_calls": choice.get("message", {}).get("tool_calls"),
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    "cost": self._estimate_cost(
                        model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    ),
                }
        except httpx.ConnectError:
            return {"error": "Cannot reach OpenRouter API"}
        except httpx.TimeoutException:
            return {"error": "OpenRouter request timed out"}

    async def chat_stream(
        self, model: str, messages: list[dict], max_tokens: int = 8000
    ) -> AsyncIterator[dict]:
        if not self.is_configured:
            yield {"error": "OpenRouter API key not configured"}
            return

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.get_headers(),
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta:
                                    yield {"content": delta["content"]}
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield {"error": str(e)}

    async def list_models(self) -> list[dict]:
        if settings.dopa_code_dummy:
            return [
                {"id": m, **info}
                for m, info in OPENROUTER_MODELS.items()
            ]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self.get_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        {
                            "id": m.get("id", ""),
                            "name": m.get("name", ""),
                            "context_length": m.get("context_length", 0),
                            "pricing": m.get("pricing", {}),
                        }
                        for m in data.get("data", [])
                    ]
                return [
                    {"id": m, **info}
                    for m, info in OPENROUTER_MODELS.items()
                ]
        except Exception:
            return [
                {"id": m, **info}
                for m, info in OPENROUTER_MODELS.items()
            ]

    async def check_credits(self) -> dict:
        if not self.is_configured:
            return {"error": "API key not configured"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/auth/key",
                    headers=self.get_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "credits_remaining": data.get("data", {}).get("credits", 0),
                        "key_label": data.get("data", {}).get("label", ""),
                    }
                return {"error": f"Auth check failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def _estimate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> dict:
        info = OPENROUTER_MODELS.get(model, {})
        pricing = info.get("pricing", {})
        prompt_cost = (prompt_tokens / 1_000_000) * pricing.get("prompt", 0)
        completion_cost = (completion_tokens / 1_000_000) * pricing.get("completion", 0)
        return {
            "prompt_cost_usd": round(prompt_cost, 6),
            "completion_cost_usd": round(completion_cost, 6),
            "total_cost_usd": round(prompt_cost + completion_cost, 6),
        }

    def _dummy_chat(self, model: str, messages: list[dict]) -> dict:
        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        return {
            "model": model,
            "content": f"[DUMMY] Response from {model} for: {user_msg[:100]}...",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            "cost": {"prompt_cost_usd": 0.000001, "completion_cost_usd": 0.000002, "total_cost_usd": 0.000003},
        }


openrouter = OpenRouterClient()


# --- Multi-Provider: APIs directas sin OpenRouter (BYOK puro) ---

PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
}


class MultiProviderClient:
    def __init__(self):
        self.providers: dict[str, str] = {}

    async def load_keys(self) -> int:
        from inti.database import async_session
        from inti.models.project_knowledge import ProjectKnowledge
        from sqlalchemy import select

        loaded = 0
        async with async_session() as session:
            result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == "dopa",
                    ProjectKnowledge.key.like("provider_key_%")
                )
            )
            for entry in result.scalars().all():
                provider = entry.key.replace("provider_key_", "")
                self.providers[provider] = entry.value
                loaded += 1

        if not loaded:
            for provider, env_key in [
                ("openai", settings.openai_api_key),
                ("anthropic", settings.anthropic_api_key),
                ("deepseek", settings.deepseek_api_key),
                ("google", settings.google_api_key),
                ("groq", settings.groq_api_key),
            ]:
                if env_key:
                    self.providers[provider] = env_key
                    loaded += 1

        return loaded

    async def configure(self, provider: str, api_key: str) -> None:
        from inti.database import async_session
        from inti.models.project_knowledge import ProjectKnowledge
        from sqlalchemy import select

        self.providers[provider] = api_key

        async with async_session() as session:
            result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == "dopa",
                    ProjectKnowledge.key == f"provider_key_{provider}"
                )
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.value = api_key
            else:
                entry = ProjectKnowledge(
                    project_id="dopa",
                    key=f"provider_key_{provider}",
                    value=api_key,
                )
                session.add(entry)
            await session.commit()

    def is_configured(self, provider: str) -> bool:
        key = self.providers.get(provider, "")
        return bool(key) and not key.endswith("...")

    async def chat(
        self, provider: str, model: str, messages: list[dict], max_tokens: int = 8000, tools: list | None = None
    ) -> dict:
        api_key = self.providers.get(provider) or getattr(settings, f"{provider}_api_key", "")

        if not api_key:
            return {"error": f"API key for {provider} not configured."}

        if settings.dopa_code_dummy:
            return {
                "content": f"[DUMMY] {provider}/{model} response",
                "model": model,
                "usage": {"total_tokens": 100},
            }

        endpoint = PROVIDER_ENDPOINTS.get(provider)
        if not endpoint:
            return {"error": f"Unknown provider: {provider}"}

        if provider == "deepseek":
            return await self._chat_openai_compat(api_key, endpoint, model, messages, max_tokens, tools)
        elif provider == "openai":
            return await self._chat_openai_compat(api_key, endpoint, model, messages, max_tokens, tools)
        elif provider == "groq":
            return await self._chat_openai_compat(api_key, endpoint, model, messages, max_tokens, tools)
        elif provider == "anthropic":
            return await self._chat_anthropic(api_key, endpoint, model, messages, max_tokens)
        elif provider == "google":
            return await self._chat_google(api_key, endpoint, model, messages, max_tokens)
        else:
            return await self._chat_openai_compat(api_key, endpoint, model, messages, max_tokens)

    async def _chat_openai_compat(
        self, api_key: str, endpoint: str, model: str, messages: list[dict], max_tokens: int, tools: list | None = None
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload: dict = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                }
                if tools:
                    payload["tools"] = tools
                resp = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code != 200:
                    return {"error": f"API error {resp.status_code}", "detail": resp.text[:500]}
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                usage = data.get("usage", {})
                return {
                    "model": data.get("model", model),
                    "content": choice.get("message", {}).get("content", ""),
                    "tool_calls": choice.get("message", {}).get("tool_calls"),
                    "finish_reason": choice.get("finish_reason", "unknown"),
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                }
        except Exception as e:
            return {"error": str(e)}

    async def _chat_anthropic(
        self, api_key: str, endpoint: str, model: str, messages: list[dict], max_tokens: int
    ) -> dict:
        try:
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
            user_msgs = [m for m in messages if m["role"] != "system"]

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    endpoint,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "system": system_msg,
                        "messages": user_msgs,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Anthropic error {resp.status_code}", "detail": resp.text[:500]}
                data = resp.json()
                content_block = data.get("content", [{}])[0]
                usage = data.get("usage", {})
                return {
                    "model": data.get("model", model),
                    "content": content_block.get("text", ""),
                    "usage": {
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    },
                }
        except Exception as e:
            return {"error": str(e)}

    async def _chat_google(
        self, api_key: str, endpoint: str, model: str, messages: list[dict], max_tokens: int
    ) -> dict:
        try:
            url = endpoint.replace("{model}", model)
            contents = []
            for m in messages:
                role = "user" if m["role"] in ("user", "system") else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": str(m["content"])}],
                })

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{url}?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": contents,
                        "generationConfig": {"maxOutputTokens": max_tokens},
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"Google error {resp.status_code}", "detail": resp.text[:500]}
                data = resp.json()
                candidates = data.get("candidates", [{}])
                content_parts = candidates[0].get("content", {}).get("parts", [{}])
                usage = data.get("usageMetadata", {})
                return {
                    "model": model,
                    "content": content_parts[0].get("text", ""),
                    "usage": {
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0),
                    },
                }
        except Exception as e:
            return {"error": str(e)}


multiprovider = MultiProviderClient()
