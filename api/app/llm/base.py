from abc import ABC, abstractmethod
from app.schemas.llm_output import LLMOutputV1


class BaseLLMProvider(ABC):
    @abstractmethod
    async def extract_learnings(self, prompt: str) -> LLMOutputV1:
        """PR データから学びを抽出する"""
        ...
