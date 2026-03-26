import json
import ollama
from app.llm.base import BaseLLMProvider
from app.schemas.llm_output import LLMOutputV1
from app.llm.anthropic_provider import SYSTEM_PROMPT


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=host)

    async def extract_learnings(self, prompt: str) -> LLMOutputV1:
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            format="json",
        )
        raw = response.message.content.strip()
        data = json.loads(raw)
        return LLMOutputV1(**data)
