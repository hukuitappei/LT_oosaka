from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db
from app.routers.auth import router as auth_router
from app.routers.github_connections import router as github_connections_router
from app.routers.health import router as health_router
from app.routers.learning_items import router as learning_items_router
from app.routers.pull_requests import router as pull_requests_router
from app.routers.repositories import router as repositories_router
from app.routers.spaces import router as spaces_router
from app.routers.weekly_digests import router as weekly_digests_router
from app.routers.webhook import router as webhook_router
from app.routers.workspaces import router as workspaces_router


def _build_lifespan():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db()
        yield

    return lifespan


def create_app(*, include_analyze_router: bool = False) -> FastAPI:
    app = FastAPI(title="PR Knowledge Hub API", version="0.1.0", lifespan=_build_lifespan())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(spaces_router)
    app.include_router(workspaces_router)
    app.include_router(github_connections_router)
    app.include_router(health_router)
    app.include_router(webhook_router)
    app.include_router(repositories_router)
    app.include_router(learning_items_router)
    app.include_router(pull_requests_router)
    app.include_router(weekly_digests_router)

    if include_analyze_router:
        from app.routers.analyze import router as analyze_router

        app.include_router(analyze_router)

    @app.get("/")
    async def root():
        return {"message": "PR Knowledge Hub API"}

    return app
