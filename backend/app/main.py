"""统一 FastAPI 应用入口。

负责注册健康检查、MySQL 管理接口，并以懒加载方式挂载旧版导入和问答服务。
"""

import os
from contextlib import asynccontextmanager
from threading import Lock
from typing import Callable

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.health import router as health_router
from backend.app.api.mysql import router as mysql_router
from backend.app.api.settings import router as settings_router
from backend.app.core.config import settings
from backend.app.core.permissions import sync_permission_registry
from backend.app.core.system_settings import sync_system_settings
from backend.app.db.session import SessionLocal


class LazyASGIApp:
    """在首次访问挂载路由时加载旧服务，兼容迁移期间的可选依赖。"""

    def __init__(self, loader: Callable[[], object]):
        self._loader = loader
        self._app = None
        self._lock = Lock()

    def _get_app(self):
        """线程安全地初始化并缓存被挂载的 ASGI 应用。"""
        if self._app is None:
            with self._lock:
                if self._app is None:
                    self._app = self._loader()
        return self._app

    async def __call__(self, scope, receive, send):
        """将 ASGI 请求转发给延迟加载的旧版服务。"""
        app = self._get_app()
        await app(scope, receive, send)


def _load_import_app():
    """导入旧版文档导入服务，仅在实际请求时执行。"""
    from web.api.import_service import app
    return app


def _load_query_app():
    """导入旧版问答服务，仅在实际请求时执行。"""
    from web.api.query_service import app
    return app


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动时同步代码注册的权限定义到数据库。"""

    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be configured before starting the API")
    if not settings.settings_encryption_key:
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY must be configured before starting the API")
    async with SessionLocal() as session:
        await sync_permission_registry(session)
        await sync_system_settings(session)
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="设备技术文档智能知识库统一 API 服务",
    lifespan=lifespan,
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
app.include_router(auth_router)
app.include_router(mysql_router)
app.include_router(settings_router)
app.mount(f"{settings.api_v1_prefix}/import", LazyASGIApp(_load_import_app), name="import-api")
app.mount(f"{settings.api_v1_prefix}/chat", LazyASGIApp(_load_query_app), name="chat-api")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """返回服务版本、文档和健康检查入口。"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": "/api",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=os.getenv("API_HOST", "127.0.0.1"), port=int(os.getenv("API_PORT", "8000")), reload=False)
