"""FastAPI dependency injection providers."""

from functools import lru_cache
from app.client.portal_client import PortalClient
from app.services.analytics_service import AnalyticsService
from app.services.hierarchy_service import HierarchyService
from app.services.meter_service import MeterService
from app.services.transformer_service import TransformerService


@lru_cache(maxsize=1)
def get_portal_client() -> PortalClient:
    """Return singleton PortalClient instance."""
    return PortalClient()


@lru_cache(maxsize=1)
def get_meter_service() -> MeterService:
    """Return singleton MeterService instance."""
    return MeterService(client=get_portal_client())


@lru_cache(maxsize=1)
def get_transformer_service() -> TransformerService:
    """Return singleton TransformerService instance."""
    return TransformerService(meter_service=get_meter_service())


@lru_cache(maxsize=1)
def get_hierarchy_service() -> HierarchyService:
    """Return singleton HierarchyService instance."""
    return HierarchyService(meter_service=get_meter_service())


@lru_cache(maxsize=1)
def get_analytics_service() -> AnalyticsService:
    """Return singleton AnalyticsService instance."""
    return AnalyticsService(meter_service=get_meter_service())
