"""API endpoints for geospatial queries and nearby meter discovery."""

from typing import List
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_meter_service
from app.models.meter import NearbyMeter
from app.services.meter_service import MeterService

router = APIRouter(prefix="/spatial", tags=["Spatial Queries"])


@router.get(
    "/nearby",
    response_model=List[NearbyMeter],
    summary="Find smart meters near coordinates",
    description=(
        "Performs a Haversine radial proximity search to locate smart meters within a given distance "
        "(in meters) of target latitude and longitude coordinates."
    ),
)
def find_nearby_meters(
    latitude: float = Query(
        ...,
        ge=-90.0,
        le=90.0,
        description="Search center latitude in decimal degrees",
        examples=[26.938961],
    ),
    longitude: float = Query(
        ...,
        ge=-180.0,
        le=180.0,
        description="Search center longitude in decimal degrees",
        examples=[75.830956],
    ),
    radius_meters: float = Query(
        5000.0,
        ge=10.0,
        le=100000.0,
        description="Maximum search radius in meters (default 5,000m = 5km)",
        examples=[3000.0],
    ),
    limit: int = Query(
        20,
        ge=1,
        le=200,
        description="Maximum number of nearby meters to return",
        examples=[20],
    ),
    meter_service: MeterService = Depends(get_meter_service),
) -> List[NearbyMeter]:
    return meter_service.find_nearby_meters(
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        limit=limit,
    )
