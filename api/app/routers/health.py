from fastapi import APIRouter
from app.config import settings
from app.services.health import check_db_health, check_llm_health

router = APIRouter()


@router.get("/health")
async def health_check():
    result = {"status": "ok", "db": "unknown", "llm": "unknown"}

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    result["db"] = await check_db_health(db_path)
    if result["db"] != "ok":
        result["status"] = "degraded"

    result["llm"] = await check_llm_health(settings.ollama_base_url)

    return result
