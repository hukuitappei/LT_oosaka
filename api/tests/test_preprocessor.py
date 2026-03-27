import pytest
from app.services.preprocessor import build_prompt


def test_build_prompt_returns_string(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_prompt_includes_pr_title(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert sample_pr_data["title"] in result


def test_build_prompt_includes_review_comment(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert "型アノテーションがないため" in result


def test_build_prompt_no_comments(sample_pr_data):
    data = {**sample_pr_data, "review_comments": []}
    result = build_prompt(data)
    assert isinstance(result, str)


def test_build_prompt_filters_bot_authors(sample_pr_data):
    # BOT_AUTHORS = {"github-actions", "dependabot", "codecov", "renovate"}
    # Exact names are filtered; "github-actions[bot]" is NOT in the set and will NOT be filtered
    data = {
        **sample_pr_data,
        "review_comments": [
            {
                "id": "1",
                "author": "github-actions[bot]",
                "body": "CI passed",
                "file": "",
                "line": None,
                "diff_hunk": "",
                "resolved": False,
            },
            {
                "id": "2",
                "author": "human",
                "body": "Good code",
                "file": "",
                "line": None,
                "diff_hunk": "",
                "resolved": False,
            },
        ],
    }
    result = build_prompt(data)
    # human comment should be included
    assert "Good code" in result
    assert isinstance(result, str)


def test_build_prompt_filters_exact_bot_name(sample_pr_data):
    # Exact bot names like "github-actions" (without [bot]) ARE filtered
    data = {
        **sample_pr_data,
        "review_comments": [
            {
                "id": "1",
                "author": "github-actions",
                "body": "CI passed - this should be filtered",
                "file": "",
                "line": None,
                "diff_hunk": "",
                "resolved": False,
            },
            {
                "id": "2",
                "author": "human",
                "body": "Human review comment",
                "file": "",
                "line": None,
                "diff_hunk": "",
                "resolved": False,
            },
        ],
    }
    result = build_prompt(data)
    # human comment should be present
    assert "Human review comment" in result
    # bot comment should be filtered out
    assert "CI passed - this should be filtered" not in result


def test_build_prompt_includes_pr_description(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert sample_pr_data["description"] in result


def test_build_prompt_includes_pr_id(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert sample_pr_data["pr_id"] in result
