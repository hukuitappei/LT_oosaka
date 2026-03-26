from fastapi import FastAPI
from app.routers.health import router as health_router
from app.routers.analyze import router as analyze_router

app = FastAPI(title="週報AI API", version="0.1.0")

app.include_router(health_router)
app.include_router(analyze_router)


@app.get("/")
async def root():
    return {"message": "週報AI API"}
