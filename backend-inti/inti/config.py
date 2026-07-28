from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Dopa Code - Inti"
    version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./dopa_code.db"
    cors_origins: list[str] = ["*"]
    jwt_secret: str = "cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    dopa_code_dummy: bool = False
    openrouter_api_key: str = ""
    antigravity_api_key: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""

    # Slugs verificados contra el catálogo vivo de OpenRouter (2026-07). Los
    # anteriores ("anthropic/claude-opus-4-8", "deepseek/deepseek-chat",
    # "antigravity") NO existían → el loop erraba/caía al fallback.
    architect_model: str = "anthropic/claude-opus-4.8-20260528"
    executor_model: str = "anthropic/claude-opus-4.8-20260528"
    qa_model: str = "anthropic/claude-opus-4.8-20260528"

    easypanel_deploy_token: str = ""
    easypanel_endpoint: str = "https://easypanel.io"

    access_token: str = "cambiar-en-produccion"

    # extra="ignore": el .env tiene claves con nombres que no matchean campos
    # (p.ej. DOPA_CODE_DUMMY vs el campo dopa_code_dummy). Sin esto,
    # pydantic-settings (extra='forbid' por default) crashea el boot del backend.
    model_config = {"env_prefix": "DOPA_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
