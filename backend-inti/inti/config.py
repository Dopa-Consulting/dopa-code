from pydantic_settings import BaseSettings
from pydantic import model_validator
import secrets


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
    bridge_token: str = ""

    model_config = {"env_prefix": "DOPA_", "env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _ensure_secrets(self):
        if self.jwt_secret == "cambiar-en-produccion":
            self.jwt_secret = secrets.token_urlsafe(32)
            import logging
            logging.getLogger("inti.config").warning(
                "DOPA_JWT_SECRET no configurado — usando valor aleatorio temporal: %s...",
                self.jwt_secret[:8]
            )
        if self.access_token == "cambiar-en-produccion":
            self.access_token = secrets.token_urlsafe(24)
            import logging
            logging.getLogger("inti.config").warning(
                "DOPA_ACCESS_TOKEN no configurado — usando valor aleatorio temporal: %s...",
                self.access_token[:8]
            )
        return self


settings = Settings()
