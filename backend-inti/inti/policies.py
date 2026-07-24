from dataclasses import dataclass, field
from typing import Literal

AutonomyLevel = Literal[
    "human_gatekeeper",
    "plan_and_pr_only",
    "auto_merge_staging",
    "full_auto",
]

TaskProfile = Literal[
    "pro_mix",
    "budget",
    "premium",
]

ProjectType = Literal[
    "dopacrm_backend",
    "dopacrm_frontend",
    "dopaweb_theme",
    "dopaweb_payment",
    "dopacrm_landing",
    "dopa_code",
]

PROJECT_TYPE_DEFAULTS: dict[ProjectType, dict] = {
    "dopacrm_backend": {
        "autonomy": "human_gatekeeper",
        "description": "Modificaciones al ERP core (backend Express + Sequelize + PostgreSQL)",
        "allowlist_extra": ["tsx", "vitest", "sequelize"],
    },
    "dopacrm_frontend": {
        "autonomy": "plan_and_pr_only",
        "description": "Dashboard PWA del CRM (Vite + React + MUI)",
        "allowlist_extra": ["vite", "playwright"],
    },
    "dopaweb_theme": {
        "autonomy": "auto_merge_staging",
        "description": "Personalizacion de templates ecommerce (Next.js + React)",
        "allowlist_extra": ["next"],
        "erp_guardrails": True,
        "skills_preset": [
            "customize_product_page",
            "customize_branding",
            "add_custom_section",
        ],
    },
    "dopaweb_payment": {
        "autonomy": "human_gatekeeper",
        "description": "Integracion BYOK de PSPs (Stripe, MercadoPago, PayPal, etc.)",
        "allowlist_extra": [],
        "erp_guardrails": True,
        "skills_preset": [
            "add_payment_method_byok",
        ],
    },
    "dopacrm_landing": {
        "autonomy": "auto_merge_staging",
        "description": "Landing page y marketing (Next.js 16 + GSAP + Stripe + Cloudflare)",
        "allowlist_extra": ["next", "opennextjs-cloudflare"],
    },
    "dopa_code": {
        "autonomy": "human_gatekeeper",
        "description": "Desarrollo del propio Dopa Code (FastAPI + React + Node bridge)",
        "allowlist_extra": ["uvicorn", "bun"],
    },
}

StepType = Literal[
    "planner",
    "executor",
    "qa",
    "deploy",
    "custom",
]

Decision = Literal["approve", "reject"]

ActorType = Literal[
    "llm_architect",
    "llm_executor",
    "llm_qa",
    "human",
    "system",
]

ALLOWED_COMMANDS: dict[str, list[str]] = {
    "git": ["status", "diff", "checkout", "commit", "push", "branch", "log", "add"],
    "python": ["-m", "pytest", "-c"],
    "npm": ["test", "run", "install", "build"],
    "opencode": [],
}


@dataclass
class ModelRole:
    provider: str
    model: str
    max_tokens: int = 8000


@dataclass
class ProfileConfig:
    name: TaskProfile
    architect: ModelRole
    executor: ModelRole
    qa: ModelRole
    default_autonomy: AutonomyLevel = "human_gatekeeper"


PROFILES: dict[TaskProfile, ProfileConfig] = {
    "pro_mix": ProfileConfig(
        name="pro_mix",
        architect=ModelRole(provider="openrouter", model="anthropic/claude-opus-4-8", max_tokens=8000),
        executor=ModelRole(provider="openrouter", model="deepseek/deepseek-chat", max_tokens=4000),
        qa=ModelRole(provider="custom", model="antigravity", max_tokens=4000),
    ),
    "budget": ProfileConfig(
        name="budget",
        architect=ModelRole(provider="openrouter", model="deepseek/deepseek-chat", max_tokens=8000),
        executor=ModelRole(provider="openrouter", model="deepseek/deepseek-chat", max_tokens=4000),
        qa=ModelRole(provider="openrouter", model="deepseek/deepseek-chat", max_tokens=4000),
    ),
    "premium": ProfileConfig(
        name="premium",
        architect=ModelRole(provider="openrouter", model="anthropic/claude-sonnet-5", max_tokens=8000),
        executor=ModelRole(provider="openrouter", model="anthropic/claude-sonnet-5", max_tokens=4000),
        qa=ModelRole(provider="openrouter", model="anthropic/claude-sonnet-5", max_tokens=4000),
    ),
}

AUTONOMY_RULES: dict[AutonomyLevel, dict] = {
    "human_gatekeeper": {
        "auto_open_pr": False,
        "auto_merge": False,
        "auto_deploy": False,
        "requires_ci_green": False,
        "allowed_branches": [],
    },
    "plan_and_pr_only": {
        "auto_open_pr": True,
        "auto_merge": False,
        "auto_deploy": False,
        "requires_ci_green": False,
        "allowed_branches": ["feature/*", "develop"],
    },
    "auto_merge_staging": {
        "auto_open_pr": True,
        "auto_merge": True,
        "auto_deploy": False,
        "requires_ci_green": True,
        "confidence_minimum": "high",
        "allowed_branches": ["develop", "staging", "feature/*"],
    },
    "full_auto": {
        "auto_open_pr": True,
        "auto_merge": True,
        "auto_deploy": True,
        "requires_ci_green": True,
        "confidence_minimum": "high",
        "allowed_branches": ["develop", "staging"],
    },
}


def get_profile(profile_name: TaskProfile) -> ProfileConfig:
    return PROFILES.get(profile_name, PROFILES["pro_mix"])


def get_autonomy_rules(level: AutonomyLevel) -> dict:
    return AUTONOMY_RULES.get(level, AUTONOMY_RULES["human_gatekeeper"])


def is_command_allowed(tool: str, args: list[str]) -> bool:
    if tool not in ALLOWED_COMMANDS:
        return False
    allowed_args = ALLOWED_COMMANDS[tool]
    if not allowed_args:
        return True
    for arg in args:
        if arg.startswith("-"):
            continue
        if arg not in allowed_args and not any(
            arg.startswith(a) for a in allowed_args
        ):
            return False
    return True


def build_safe_command(tool: str, args: list[str]) -> list[str]:
    if not is_command_allowed(tool, args):
        raise ValueError(f"Comando no permitido: {tool} {args}")
    return [tool] + args
