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
    assert sample_pr_data["review_comments"][0]["body"] in result


def test_build_prompt_no_comments(sample_pr_data):
    data = {**sample_pr_data, "review_comments": []}
    result = build_prompt(data)
    assert isinstance(result, str)


def test_build_prompt_filters_bot_authors(sample_pr_data):
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
    assert "Good code" in result
    assert isinstance(result, str)


def test_build_prompt_filters_exact_bot_name(sample_pr_data):
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
    assert "Human review comment" in result
    assert "CI passed - this should be filtered" not in result


def test_build_prompt_includes_pr_description(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert sample_pr_data["description"] in result


def test_build_prompt_includes_pr_id(sample_pr_data):
    result = build_prompt(sample_pr_data)
    assert sample_pr_data["pr_id"] in result
