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
    },
    "google/gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "provider": "Google",
        "context_length": 1048576,
        "max_output": 8192,
        "pricing": {
            "prompt": 1.25,
            "completion": 10.00,
        },
        "capabilities": ["reasoning", "code", "multimodal"],
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
    },
}


class OpenRouterClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = OPENROUTER_API

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

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
