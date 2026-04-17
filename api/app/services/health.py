import httpx
import aiosqlite


async def check_db_health(db_path: str) -> str:
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")
        return "ok"
    except Exception as e:
        return f"error: {str(e)}"


async def check_llm_health(ollama_base_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_base_url}/api/tags")
            if resp.status_code == 200:
                return "ok"
            return f"http {resp.status_code}"
    except Exception:
        return "not running"
