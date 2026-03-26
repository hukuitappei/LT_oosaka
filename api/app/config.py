from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./lt_oosaka.db"
    ollama_base_url: str = "http://localhost:11434"
    secret_key: str = "changeme"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
