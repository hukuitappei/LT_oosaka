import httpx
from typing import Any


class GitHubClient:
    """GitHub API クライアント (GitHub App installation token 使用)"""

    BASE_URL = "https://api.github.com"

    def __init__(self, installation_token: str):
        self.headers = {
            "Authorization": f"Bearer {installation_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_review_comments(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()
