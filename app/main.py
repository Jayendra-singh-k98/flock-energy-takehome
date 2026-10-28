"""Urja Meter Ops Modern API Bridge — Main Application Entry Point."""

from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.config import settings
from app.dependencies import get_meter_service

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("urja.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    logger.info("Initializing Urja Meter Ops API Service...")
    logger.info("Connecting to upstream portal: %s", settings.portal_base_url)

    if settings.auto_sync_on_startup:
        logger.info("Pre-warming in-memory index and cache from Urja Meter Ops...")
        try:
            meter_svc = get_meter_service()
            result = meter_svc.sync_all(force=True)
            logger.info("Startup pre-warm complete: %s", result)
        except Exception as exc:
            logger.warning("Startup pre-warm failed (will retry on first request): %s", exc)

    yield

    logger.info("Urja Meter Ops API Service shutdown complete.")


app = FastAPI(
    title="Urja Meter Ops API Bridge",
    description=(
        "Clean, documented, high-performance REST API service built over the legacy "
        "Urja Meter Ops smart-meter portal. Exposes normalized meter specifications, "
        "reconstructed 7-tier electrical distribution hierarchy, interval telemetry analytics, "
        "and geospatial radius queries."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router)

# Mount Static directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the modern web client dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "service": "Urja Meter Ops API Bridge",
        "status": "running",
        "documentation": "/docs",
    }


@app.get(
    "/health",
    tags=["System & Synchronization"],
    summary="Liveness probe",
    status_code=status.HTTP_200_OK,
)
def health_check():
    """Basic health check probe for load balancers and orchestrators."""
    return {"status": "ok", "service": "urja-meter-ops-bridge"}
