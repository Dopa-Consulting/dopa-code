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
    run_command_timeout: int = 120
    # Máximo de pasos observar→actuar por tarea. Estaba hardcodeado en 4 (bajado
    # para no quemar $ con Opus), lo que hacía que Inti se rindiera en tareas
    # multi-paso ("He ejecutado 4 pasos sin completar"). Con modelo barato el
    # costo de más pasos es mínimo; el guard de tool-calls repetidos evita spin.
    # Configurable via DOPA_MAX_ITERATIONS.
    max_iterations: int = 20
    openrouter_api_key: str = ""
    antigravity_api_key: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""

    architect_model: str = "anthropic/claude-sonnet-5"
    executor_model: str = "deepseek-v4-flash"
    qa_model: str = "anthropic/claude-sonnet-5"

    loop_model: str = "deepseek/deepseek-chat"  # Via OpenRouter (como Hermes)
    heavy_model: str = "anthropic/claude-sonnet-5"

    easypanel_deploy_token: str = ""
    easypanel_endpoint: str = "https://easypanel.io"
    access_token: str = "cambiar-en-produccion"

    model_config = {"env_prefix": "DOPA_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
