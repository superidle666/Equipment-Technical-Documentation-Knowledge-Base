"""Unified FastAPI entry point.

The existing import and query applications are mounted under versioned API
groups. They are loaded on first request so a liveness check does not eagerly
initialize MinIO clients, embedding models, or other external dependencies.
"""

import os
from threading import Lock
from typing import Callable

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.core.config import settings


class LazyASGIApp:
    """Load an existing FastAPI app only when its mounted route is used."""

    def __init__(self, loader: Callable[[], object]):
        self._loader = loader
        self._app = None
        self._lock = Lock()

    def _get_app(self):
        if self._app is None:
            with self._lock:
                if self._app is None:
                    self._app = self._loader()
        return self._app

    async def __call__(self, scope, receive, send):
        app = self._get_app()
        await app(scope, receive, send)


def _load_import_app():
    from web.api.import_service import app

    return app


def _load_query_app():
    from web.api.query_service import app

    return app


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="设备技术文档智能知识库统一 API 服务",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)

# Migration-compatible mounted groups. The original web/api files remain
# runnable independently on ports 8000 and 8001 during the transition.
app.mount(
    f"{settings.api_v1_prefix}/import",
    LazyASGIApp(_load_import_app),
    name="import-api",
)
app.mount(
    f"{settings.api_v1_prefix}/chat",
    LazyASGIApp(_load_query_app),
    name="chat-api",
)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": "/api",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=False,
    )

