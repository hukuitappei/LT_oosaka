from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "sqlite+aiosqlite:///./lt_oosaka.db"
    redis_url: str = "redis://localhost:6379/0"
    ollama_base_url: str = "http://localhost:11434"
    secret_key: str = "changeme"
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    app_env: str = "production"
    weekly_digest_schedule_minute: int = 0
    weekly_digest_schedule_hour: int = 9
    weekly_digest_schedule_day_of_week: str = "mon"
    # GitHub App
    github_app_id: str = ""
    github_private_key: str = ""
    github_webhook_secret: str = ""
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"


settings = Settings()
