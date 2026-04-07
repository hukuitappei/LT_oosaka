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
    # GitHub App
    github_app_id: str = ""
    github_private_key: str = ""
    github_webhook_secret: str = ""
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    github_connection_token_encryption_key: str = ""
    pr_retention_days: int = 90
    log_retention_days: int = 30
    learning_retention_days: int = 365
    digest_retention_days: int = 365
    loki_push_url: str = ""
    loki_username: str = ""
    loki_password: str = ""
    loki_tenant_id: str = ""
    loki_retention_job: str = "lt_oosaka-retention"
    loki_timeout_seconds: float = 5.0


settings = Settings()
