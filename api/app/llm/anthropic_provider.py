import json
import anthropic
from app.llm.base import BaseLLMProvider
from app.schemas.llm_output import LLMOutputV1

SYSTEM_PROMPT = """あなたはソフトウェアエンジニアのコードレビュー分析の専門家です。
GitHubのPRレビューコメントを分析し、次回に再利用できる「学び」を構造化して抽出します。

以下のJSONスキーマに厳密に従って出力してください。Markdownやコードブロックは使わず、JSONのみ返してください。

{
  "schema_version": "1.0",
  "source": "<PR ID>",
  "summary": "<PRの概要1〜2文>",
  "learning_items": [
    {
      "title": "<学びのタイトル20字以内>",
      "detail": "<詳細説明>",
      "category": "<security|performance|design|testing|code_quality|other>",
      "confidence": <0.0〜1.0>,
      "action_for_next_time": "<次回の具体的アクション>",
      "evidence": "<根拠となるレビューコメントの引用>"
    }
  ],
  "repeated_issues": ["<繰り返しパターン>"],
  "next_time_notes": ["<次回の自分へのメモ>"]
}"""


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def extract_learnings(self, prompt: str) -> LLMOutputV1:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        return LLMOutputV1(**data)
