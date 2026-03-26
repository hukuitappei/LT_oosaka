from typing import Literal
from pydantic import BaseModel, Field


class LearningItem(BaseModel):
    title: str = Field(description="学びのタイトル（20字以内）")
    detail: str = Field(description="詳細説明")
    category: str = Field(description="カテゴリ: security / performance / design / testing / code_quality / other")
    confidence: float = Field(ge=0.0, le=1.0, description="確信度 0.0〜1.0")
    action_for_next_time: str = Field(description="次回の具体的なアクション")
    evidence: str = Field(description="根拠となるレビューコメントの引用")


class LLMOutputV1(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    source: str = Field(description="PR ID")
    summary: str = Field(description="PRの概要（1〜2文）")
    learning_items: list[LearningItem]
    repeated_issues: list[str] = Field(default_factory=list, description="繰り返しやすい詰まりパターン")
    next_time_notes: list[str] = Field(default_factory=list, description="次回の自分へのメモ")
