"""API endpoints for querying, filtering, and inspecting smart meters."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_meter_service
from app.models.common import PaginatedResponse, PaginationMeta
from app.models.meter import EnergySummary, GeoLocation, MeterDetail, MeterSummary
from app.services.meter_service import MeterService

router = APIRouter(prefix="/meters", tags=["Smart Meters"])


@router.get(
    "",
    response_model=PaginatedResponse[MeterSummary],
    summary="List and filter smart meters",
    description=(
        "Query smart meters across hardware attributes, electrical phase, "
        "operational status, connected distribution transformer, or network hierarchy."
    ),
)
def list_meters(
    q: Optional[str] = Query(
        None, description="Search substring in Meter ID or Hardware Serial Number"
    ),
    make: Optional[str] = Query(
        None, description="Filter by hardware manufacturer (e.g. HPL, Genus, Secure, Allied, L&T)"
    ),
    phase_type: Optional[str] = Query(
        None, description="Filter by electrical phase (single, three)"
    ),
    install_status: Optional[str] = Query(
        None, description="Filter by status (Installed, Faulty, Decommissioned)"
    ),
    dt_code: Optional[str] = Query(
        None, description="Filter by connected Distribution Transformer code (e.g. DT-001)"
    ),
    feeder_code: Optional[str] = Query(
        None, description="Filter by Feeder code (e.g. F-001)"
    ),
    zone_code: Optional[str] = Query(
        None, description="Filter by Zone code (e.g. Z-01)"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    meter_service: MeterService = Depends(get_meter_service),
) -> PaginatedResponse[MeterSummary]:
    skip = (page - 1) * page_size
    items, total = meter_service.query_meters(
        query=q,
        make=make,
        phase_type=phase_type,
        install_status=install_status,
        dt_code=dt_code,
        feeder_code=feeder_code,
        zone_code=zone_code,
        skip=skip,
        limit=page_size,
    )

    pagination = PaginationMeta.create(page=page, page_size=page_size, total_items=total)
    return PaginatedResponse(data=items, pagination=pagination)


@router.get(
    "/{meter_id}",
    response_model=MeterDetail,
    summary="Get meter detail",
    description="Retrieve comprehensive smart meter details including full 7-tier distribution hierarchy.",
)
def get_meter(
    meter_id: str,
    meter_service: MeterService = Depends(get_meter_service),
) -> MeterDetail:
    meter = meter_service.get_meter_by_id(meter_id)
    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter with ID '{meter_id}' not found.",
        )
    return meter


@router.get(
    "/{meter_id}/energy",
    response_model=EnergySummary,
    summary="Get meter energy telemetry",
    description=(
        "Fetch 30-minute interval smart-meter telemetry readings, total active consumption delta, "
        "voltage statistics, and automatic voltage anomaly checks."
    ),
)
def get_meter_energy(
    meter_id: str,
    meter_service: MeterService = Depends(get_meter_service),
) -> EnergySummary:
    # First verify meter exists
    if not meter_service.get_meter_by_id(meter_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter with ID '{meter_id}' not found.",
        )
    try:
        return meter_service.get_meter_energy(meter_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch upstream energy readings for meter '{meter_id}': {exc}",
        ) from exc


@router.get(
    "/{meter_id}/geo",
    response_model=GeoLocation,
    summary="Get meter geographic coordinates",
    description="Fetch normalized latitude and longitude coordinates for a smart meter.",
)
def get_meter_geo(
    meter_id: str,
    meter_service: MeterService = Depends(get_meter_service),
) -> GeoLocation:
    geo = meter_service.get_meter_geo(meter_id)
    if not geo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geographic coordinates unavailable for meter '{meter_id}'.",
        )
    return geo
