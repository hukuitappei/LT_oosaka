from __future__ import annotations

from app.config import settings
from app.llm.base import BaseLLMProvider


def get_llm_provider(provider_name: str) -> BaseLLMProvider:
    if provider_name == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=settings.anthropic_api_key)

    if provider_name == "ollama":
        if not settings.ollama_base_url:
            raise ValueError("OLLAMA_BASE_URL not configured")
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider(host=settings.ollama_base_url)

    raise ValueError(f"Unknown provider: {provider_name}")


def get_default_llm_provider() -> BaseLLMProvider:
    if settings.anthropic_api_key:
        return get_llm_provider("anthropic")
    if settings.ollama_base_url:
        return get_llm_provider("ollama")
    raise ValueError("No LLM provider configured")
