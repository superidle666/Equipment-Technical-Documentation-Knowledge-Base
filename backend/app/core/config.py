"""Centralized configuration for the unified API service.

This module intentionally contains only configuration that is needed by the
API shell. Feature-specific settings remain in the existing config modules
until their services are migrated.
"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def _csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    """Parse a comma-separated environment variable into non-empty values."""

    if not value:
        return default
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    return values or default


@dataclass(frozen=True)
class Settings:
    """Settings used by the unified FastAPI shell."""

    app_name: str = os.getenv(
        "APP_NAME", "设备技术文档智能知识库平台"
    )
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    environment: str = os.getenv("APP_ENV", "development")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    cors_allow_origins: tuple[str, ...] = _csv(
        os.getenv("CORS_ALLOW_ORIGINS"), ("*",)
    )


settings = Settings()

