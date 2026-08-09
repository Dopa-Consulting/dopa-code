"""Loop Cost — tracking de tokens y costo USD por job."""

# Precios por millon de tokens (input/output). Actualizado 2025.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek/deepseek-v4-pro": {"input": 0.50, "output": 2.00},
    "deepseek-v4-pro": {"input": 0.50, "output": 2.00},
    "anthropic/claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "anthropic/claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "google/gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "google/gemini-2.5-flash-image": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


class LoopCost:
    def __init__(self, model: str):
        self.model = model
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.iterations = 0

    def add_usage(self, usage: dict | None):
        if not usage:
            return
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.iterations += 1

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_usd(self) -> float:
        pricing = MODEL_PRICING.get(self.model, {"input": 1.0, "output": 5.0})
        input_cost = (self.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.completion_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "iterations": self.iterations,
        }


def estimate_cost(model: str, usage: dict) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 5.0})
    pt = usage.get("prompt_tokens", 0)
    ct = usage.get("completion_tokens", 0)
    return round(((pt / 1_000_000) * pricing["input"]) + ((ct / 1_000_000) * pricing["output"]), 6)
