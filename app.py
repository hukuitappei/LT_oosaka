import os
import re
import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="アイデア中立評価",
    page_icon="💡",
    layout="centered",
)

MODEL = "claude-haiku-4-5-20251001"

EXAMPLE_IDEAS = [
    "AIを使って会議の議事録を自動で要約するサービス",
    "エンジニアの勉強記録をゲーム化するアプリ",
    "地域の空き店舗とポップアップ出店者をマッチングするプラットフォーム",
]

SYSTEM_PROMPT = """あなたは経験豊富なベンチャーキャピタリストとプロダクトマネージャーの視点を持つ、
中立的なアイデア評価者です。感情的な応援も過度な批判もせず、事実と論理に基づいて評価します。

ユーザーからアイデアが送られたら、必ず以下のフォーマットで回答してください。
フォーマット以外の前置きや後書きは一切不要です。

---
## 良い点
1. （強み1）
2. （強み2）
3. （強み3）

## 懸念点
1. （懸念1）
2. （懸念2）
3. （懸念3）

## 実現可能性スコア
SCORE: X/10
（スコアの根拠を1〜2文で説明）

## 改善提案
1. （改善提案1）
2. （改善提案2）

## 一言まとめ
（このアイデアの本質を20字以内で表現する、歯切れの良いひと言）
---
"""


def extract_score(text: str) -> int | None:
    match = re.search(r"SCORE:\s*(\d+)/10", text)
    if match:
        return max(1, min(10, int(match.group(1))))
    return None


# --- UI ---
st.title("💡 あなたのアイデアを中立的に評価しよう")
st.caption("AIが良い点・懸念点・実現可能性を公平に分析します")

st.subheader("入力例（クリックで反映）")
cols = st.columns(3)
for i, (col, idea) in enumerate(zip(cols, EXAMPLE_IDEAS)):
    if col.button(idea[:18] + "…", key=f"example_{i}"):
        st.session_state["idea_input"] = idea

idea = st.text_area(
    "アイデアを入力",
    value=st.session_state.get("idea_input", ""),
    height=120,
    placeholder="例：AIを使って〇〇するサービス、アプリ、仕組みなど",
    key="idea_input",
)

evaluate_btn = st.button(
    "🔍 評価する",
    type="primary",
    use_container_width=True,
    disabled=(not idea.strip()),
)

if evaluate_btn and idea.strip():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)

    st.divider()
    st.subheader("📊 評価結果")

    score_placeholder = st.empty()
    result_placeholder = st.empty()
    full_text = ""

    with st.spinner("評価中..."):
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": idea}],
        ) as stream:
            for chunk in stream.text_stream:
                full_text += chunk

                score = extract_score(full_text)
                if score is not None:
                    with score_placeholder.container():
                        col1, col2 = st.columns([1, 3])
                        col1.metric("実現可能性", f"{score}/10")
                        col2.progress(score / 10)

                result_placeholder.markdown(full_text)

    final_score = extract_score(full_text)
    if final_score is not None:
        st.success(f"評価完了！ 実現可能性スコア: {final_score}/10")

    summary_match = re.search(r"## 一言まとめ\n(.+)", full_text)
    if summary_match:
        st.info(f"**一言まとめ：** {summary_match.group(1).strip()}", icon="💬")
