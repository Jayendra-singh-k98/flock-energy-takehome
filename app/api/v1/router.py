"""API v1 master router."""

from fastapi import APIRouter
from app.api.v1.analytics import router as analytics_router
from app.api.v1.hierarchy import router as hierarchy_router
from app.api.v1.meters import router as meters_router
from app.api.v1.spatial import router as spatial_router
from app.api.v1.sync import router as sync_router
from app.api.v1.transformers import router as transformers_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(meters_router)
api_v1_router.include_router(transformers_router)
api_v1_router.include_router(hierarchy_router)
api_v1_router.include_router(spatial_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(sync_router)
