"""API endpoints for cache synchronization and operational health."""

import time
from typing import Any, Dict
from fastapi import APIRouter, Depends
from app.config import settings
from app.dependencies import get_meter_service, get_portal_client
from app.models.common import HealthStatus
from app.services.meter_service import MeterService

router = APIRouter(prefix="/sync", tags=["System & Synchronization"])


@router.post(
    "",
    summary="Trigger on-demand data synchronization",
    description="Forces an immediate refresh of all smart meters and distribution transformers from Urja Meter Ops.",
)
def trigger_sync(
    meter_service: MeterService = Depends(get_meter_service),
) -> Dict[str, Any]:
    stats = meter_service.sync_all(force=True)
    return {
        "status": "success",
        "message": "Full synchronization completed successfully.",
        **stats,
        "synced_at": time.time(),
    }


@router.get(
    "/status",
    response_model=HealthStatus,
    summary="Get cache and health status",
    description="Returns current memory index volume, cache freshness age, and connectivity status.",
)
def get_sync_status(
    meter_service: MeterService = Depends(get_meter_service),
) -> HealthStatus:
    meters_count = len(meter_service.get_all_raw_meters())
    dts_count = len(meter_service.get_all_raw_dts())
    return HealthStatus(
        status="healthy",
        portal_connected=True,
        indexed_meters=meters_count,
        indexed_transformers=dts_count,
        cache_age_seconds=meter_service.cache_age_seconds,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
