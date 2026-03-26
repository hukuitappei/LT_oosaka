from fastapi import APIRouter
import httpx
import aiosqlite
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    result = {"status": "ok", "db": "unknown", "llm": "unknown"}

    # DB check (SQLite)
    try:
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {str(e)}"
        result["status"] = "degraded"

    # Ollama check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                result["llm"] = "ok"
            else:
                result["llm"] = f"http {resp.status_code}"
    except Exception:
        result["llm"] = "not running"

    return result
