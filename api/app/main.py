from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers.health import router as health_router
from app.routers.analyze import router as analyze_router
from app.routers.webhook import router as webhook_router
from app.routers.repositories import router as repositories_router
from app.routers.learning_items import router as learning_items_router
from app.routers.pull_requests import router as pull_requests_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="週報AI API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(webhook_router)
app.include_router(repositories_router)
app.include_router(learning_items_router)
app.include_router(pull_requests_router)


@app.get("/")
async def root():
    return {"message": "週報AI API"}
