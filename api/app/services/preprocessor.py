from typing import Any

BOT_AUTHORS = {"github-actions", "dependabot", "codecov", "renovate"}

def normalize_comments(pr_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    レビューコメントを正規化する:
    - bot コメントを除去
    - 返信（is_reply=True）をメインコメントに統合
    - 解決済み・未解決の両方を保持
    """
    comments = pr_data.get("review_comments", [])
    # botコメント除去
    comments = [c for c in comments if c.get("author", "").lower() not in BOT_AUTHORS]
    # 返信は証跡として保持するが、is_reply フラグを付ける
    return comments


def build_prompt(pr_data: dict[str, Any]) -> str:
    """PR データを LLM への入力プロンプトに変換する"""
    comments = normalize_comments(pr_data)

    lines = [
        f"## PR: {pr_data.get('title', '')}",
        f"PR ID: {pr_data.get('pr_id', '')}",
        f"説明: {pr_data.get('description', '')}",
        f"変更概要: {pr_data.get('diff_summary', '')}",
        "",
        "## レビューコメント",
    ]

    for i, c in enumerate(comments, 1):
        is_reply = c.get("is_reply", False)
        resolved = "[resolved]" if c.get("resolved") else "[unresolved]"
        prefix = "  reply" if is_reply else f"### Comment {i}"
        lines.append(f"{prefix} [{resolved}] by {c.get('author', '')}")
        lines.append(f"ファイル: {c.get('file', '')} L{c.get('line', '')}")
        if c.get("diff_hunk"):
            lines.append(f"```\n{c['diff_hunk']}\n```")
        lines.append(c.get("body", ""))
        lines.append("")

    lines.append("上記のレビューコメントから、再利用可能な学びを抽出してください。")
    return "\n".join(lines)
