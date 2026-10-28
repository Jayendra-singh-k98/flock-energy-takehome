"""API endpoints for grid analytics, fleet statistics, and anomaly reports."""

from fastapi import APIRouter, Depends
from app.dependencies import get_analytics_service
from app.models.analytics import FleetAnomalies, FleetOverview
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Grid Analytics"])


@router.get(
    "/overview",
    response_model=FleetOverview,
    summary="Get fleet overview and hardware breakdown",
    description="Returns aggregate counts of smart meters by manufacturer, electrical phase, status, and transformer capacity.",
)
def get_fleet_overview(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> FleetOverview:
    return analytics_service.get_fleet_overview()


@router.get(
    "/anomalies",
    response_model=FleetAnomalies,
    summary="Get fleet operational anomalies",
    description="Identifies meters requiring operational intervention, including faulty units and voltage anomalies.",
)
def get_fleet_anomalies(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> FleetAnomalies:
    return analytics_service.get_fleet_anomalies()
