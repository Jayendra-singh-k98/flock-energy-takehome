"""Configuration module for the Urja Meter Ops API Service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings and configuration parameters."""

    # Upstream portal settings
    portal_base_url: str = os.getenv(
        "PORTAL_BASE_URL", "https://urja-ops.flockenergy.tech"
    ).rstrip("/")
    portal_username: str = os.getenv("PORTAL_USERNAME", "operator@urja.local")
    portal_password: str = os.getenv("PORTAL_PASSWORD", "urja-ops-2026")

    # Service cache and synchronization
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))  # 15 minutes
    auto_sync_on_startup: bool = (
        os.getenv("AUTO_SYNC_ON_STARTUP", "true").lower() == "true"
    )

    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "production")


settings = Settings()
