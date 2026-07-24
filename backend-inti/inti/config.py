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

    architect_model: str = "anthropic/claude-opus-4-8"
    executor_model: str = "deepseek/deepseek-chat"
    qa_model: str = "antigravity"

    easypanel_deploy_token: str = ""
    easypanel_endpoint: str = "https://easypanel.io"

    model_config = {"env_prefix": "DOPA_", "env_file": ".env"}


settings = Settings()
