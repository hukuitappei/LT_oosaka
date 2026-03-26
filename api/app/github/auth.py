import time
import jwt
import httpx
from app.config import settings


def generate_jwt() -> str:
    """GitHub App の JWT を生成する"""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, settings.github_private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """installation_id から access token を取得する"""
    app_jwt = generate_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]
