"""Liveness and API discovery endpoints."""

from fastapi import APIRouter

from backend.app.core.config import settings


router = APIRouter(tags=["system"])


@router.get("/health", summary="服务健康检查")
async def health() -> dict:
    """Return a lightweight liveness response without external dependencies."""

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "status": "ok",
            "service": "knowledge-base-api",
            "version": settings.app_version,
            "environment": settings.environment,
        },
    }


@router.get("/api", summary="API 能力列表")
async def api_index() -> dict:
    """Describe the stable mounted API groups during the migration period."""

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "name": settings.app_name,
            "version": settings.app_version,
            "groups": {
                "import": f"{settings.api_v1_prefix}/import",
                "chat": f"{settings.api_v1_prefix}/chat",
            },
            "legacy_services": {
                "import": "web/api/import_service.py (default port 8000)",
                "chat": "web/api/query_service.py (default port 8001)",
            },
        },
    }

