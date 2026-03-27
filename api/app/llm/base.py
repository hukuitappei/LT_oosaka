from abc import ABC, abstractmethod
from app.schemas.llm_output import LLMOutputV1


class BaseLLMProvider(ABC):
    @abstractmethod
    async def extract_learnings(self, prompt: str) -> LLMOutputV1:
        """PR データから学びを抽出する"""
        ...

    @abstractmethod
    async def generate_text(self, system_prompt: str, user_message: str) -> str:
        """汎用テキスト生成（週報など）"""
        ...
